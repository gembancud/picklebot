"""Training-only centralized value model and independent-player PPO math."""
import torch
import math
import copy
from collections import defaultdict
from torch import nn
from torch.distributions import Bernoulli, Categorical, Normal


def validate_motor_metrics(report):
    """Reject unsafe independent-player rollouts before optimization."""
    limits = {"playerMaxSpeed": 3.801, "playerMaxAcceleration": 14.05,
              "playerMaxPaddleSpeed": 12.01, "playerMaxPaddleAcceleration": 100.1,
              "playerMaxReach": .6201}
    if not report.get("games"):
        raise ValueError("Missing game motor measurements")
    for game in report["games"]:
        team = game.get("candidateTeam")
        metrics = game.get("metrics", {})
        if type(team) is not int or team not in (0, 1):
            raise ValueError("Invalid motor measurement ownership")
        if metrics.get("infeasiblePaddleSteps") != 0:
            raise ValueError("Infeasible independent paddle steps in rollout")
        for name, limit in limits.items():
            values = metrics.get(name)
            if not isinstance(values, list) or len(values) != 4:
                raise ValueError("Missing per-player motor measurements: " + name)
            # The unchanged baseline has a different motor. Saved actor
            # opponents use the same independent motor as the candidate,
            # so both teams must pass when that opponent mode is active.
            players = range(4) if report.get("opponentMode") == "older actor / sampled" else range(team * 2, team * 2 + 2)
            for player in players:
                value = values[player]
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= limit:
                    raise ValueError(f"Independent motor bound failed: player {player}, {name}={value}")


def freeze_nonshot_heads(actor):
    """Train only shot logits on a newly loaded actor. No movement/hit drift."""
    for layer in actor.layers[:-1]:
        layer.requires_grad_(False)
    actor.log_std.requires_grad_(False)
    # Adam has no weight decay in this trainer. Zero gradients keep these
    # protected rows exactly unchanged; the trainer also verifies the result.
    def shots_only(gradient):
        result = gradient.clone(); result[:3] = 0
        return result
    actor.layers[-1].weight.register_hook(shots_only)
    actor.layers[-1].bias.register_hook(shots_only)


def nonshot_parameters(actor):
    return [p.detach().clone() for layer in actor.layers[:-1] for p in layer.parameters()] + [
        actor.layers[-1].weight[:3].detach().clone(), actor.layers[-1].bias[:3].detach().clone(),
        actor.log_std.detach().clone()]


def return_parameters(reward_mode, credit_assignment="default"):
    """Keep game-win returns unchanged; permit a full-rally curriculum trial."""
    if reward_mode not in ("rally_win", "game_win") or credit_assignment not in ("default", "full_episode"):
        raise ValueError("Unknown reward objective or credit assignment")
    return (1.0, 1.0) if reward_mode == "game_win" or credit_assignment == "full_episode" else (.995, .95)


class Critic(nn.Module):
    def __init__(self):
        super().__init__()
        # Current own and teammate observations only. Never loaded in Unity.
        self.layers = nn.Sequential(nn.Linear(108, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, 1))

    def forward(self, observation):
        return self.layers(observation).squeeze(-1)


def log_probability(actor, observation, raw_move, attempt, shot):
    output = actor(observation)
    # The stored action is the pre-transform Gaussian variable. Its deterministic
    # tanh/radial conversion is unchanged, so PPO ratios use this latent density.
    move = Normal(output[:, :2], actor.log_std.clamp(-5, 1).exp())
    hit = Bernoulli(logits=output[:, 2])
    target = Categorical(logits=output[:, 3:])
    logp = move.log_prob(raw_move).sum(-1) + hit.log_prob(attempt) + target.log_prob(shot)
    entropy = move.entropy().sum(-1) + hit.entropy() + target.entropy()
    return logp, entropy


def advantages(rewards, values, terminal, gamma=.995, gae_lambda=.95):
    """One complete player trajectory. Never cross a game/episode boundary."""
    if not (len(rewards) == len(values) == len(terminal)) or not len(rewards):
        raise ValueError("Invalid trajectory lengths")
    if not terminal[-1]:
        raise ValueError("Complete trajectories are required; missing bootstrap state")
    result = torch.zeros_like(values); carry = torch.zeros((), dtype=values.dtype)
    for t in range(len(values) - 1, -1, -1):
        continuation = 1.0 - terminal[t].float()
        next_value = values[t + 1] if t + 1 < len(values) else 0.0
        delta = rewards[t] + gamma * next_value * continuation - values[t]
        carry = delta + gamma * gae_lambda * continuation * carry
        result[t] = carry
    return result, result + values


def clipped_loss(logp, old_logp, advantage, clip=.2):
    ratio = (logp - old_logp).exp()
    loss = -torch.minimum(ratio * advantage, ratio.clamp(1 - clip, 1 + clip) * advantage).mean()
    # Non-negative approximation to KL(old || new) on the old-policy samples.
    kl = ((ratio - 1) - (logp - old_logp)).mean()
    return loss, kl


def prepare_advantages(advantage, normalization="standard"):
    """Keep an explicit baseline choice; never silently learn from entropy alone."""
    if (advantage.ndim != 1 or not len(advantage) or not torch.isfinite(advantage).all()
            or normalization not in ("standard", "none")):
        raise ValueError("Invalid policy advantages or normalization mode")
    result = advantage.detach().clone()
    if normalization == "standard":
        result = (result-result.mean())/result.std(unbiased=False).clamp_min(1e-6)
    if not bool(result.abs().max() > 0):
        raise ValueError("No game/rally policy-gradient signal after advantage processing; no actor update is allowed")
    return result


def bounded_optimizer_step(actor, critic, actor_optimizer, critic_optimizer, loss, measure_kl, target_kl):
    """Apply one step atomically; restore both networks and Adam state on rejection."""
    if not math.isfinite(target_kl) or target_kl <= 0:
        raise ValueError("Invalid post-update KL bound")
    states = (actor, critic, actor_optimizer, critic_optimizer)
    before = tuple(copy.deepcopy(item.state_dict()) for item in states)
    try:
        actor_optimizer.zero_grad(set_to_none=True); critic_optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(actor.parameters(), .5)
        torch.nn.utils.clip_grad_norm_(critic.parameters(), .5)
        actor_optimizer.step(); critic_optimizer.step()
        with torch.no_grad():
            actor.log_std.clamp_(-5, 1)
            measured = float(measure_kl())
        accepted = math.isfinite(measured) and 0 <= measured <= target_kl
    except Exception:
        for item, state in zip(states, before): item.load_state_dict(state)
        raise
    if not accepted:
        for item, state in zip(states, before): item.load_state_dict(state)
    return accepted, measured


def validate_episodes(records, report):
    """Check reward ownership, paired observations and terminal placement."""
    groups = defaultdict(list); paired = defaultdict(dict); rallies = defaultdict(list)
    games = {game["gameSeed"]: game for game in report["games"]}
    for rally in report["rallies"]: rallies[rally["gameSeed"]].append(rally)
    for index, row in enumerate(records):
        if row["player"] // 2 != row["candidateTeam"]:
            raise ValueError("Opponent data entered the actor update")
        groups[(row["episode"], row["player"])].append(index)
        key = (row["episode"], row["rally"], row["tick"])
        if row["player"] in paired[key]: raise ValueError("Duplicate player decision")
        paired[key][row["player"]] = row
    for pair in paired.values():
        if len(pair) != 2: raise ValueError("Missing simultaneous teammate decision")
        for player, row in pair.items():
            partner = pair.get(player ^ 1)
            if partner is None or partner["candidateTeam"] != row["candidateTeam"] or partner["gameSeed"] != row["gameSeed"]:
                raise ValueError("Mixed team or game observations")
            if row["criticObservation"] != row["observation"] + partner["observation"]:
                raise ValueError("Critic observation does not match this simultaneous player pair")
    for indices in groups.values():
        sequence = [records[index] for index in indices]; last = sequence[-1]
        if not last["terminal"] or any(row["terminal"] or row["reward"] != 0 for row in sequence[:-1]):
            raise ValueError("Reward or terminal flag is not at the episode end")
        if any(row["gameSeed"] != last["gameSeed"] or row["candidateTeam"] != last["candidateTeam"] for row in sequence):
            raise ValueError("Episode crosses a game or team boundary")
        winner = games[last["gameSeed"]]["winner"] if report["rewardMode"] == "game_win" else rallies[last["gameSeed"]][last["rally"]]["winner"]
        expected = 0 if winner < 0 else 1 if winner == last["candidateTeam"] else -1
        if last["reward"] != expected: raise ValueError("Player reward differs from the recorded team result")
    return groups
