"""Read-only transport logging around the installed ML-Agents trainer."""
import os,json,inspect,hashlib
from pathlib import Path
from mlagents.trainers.agent_processor import AgentProcessor,AgentManager
from mlagents_envs.base_env import TerminalStep
from mlagents.trainers.learn import main
if __name__=="__main__":
 path=Path(os.environ["PICKLEBOT_DELIVERY_AUDIT"])
 stream=path.open("x",encoding="utf-8",buffering=1)
 def record(x):stream.write(json.dumps(x)+"\n")
 source=Path(inspect.getfile(AgentProcessor))
 record(dict(kind="identity",source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),wrapperSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
 original_step=AgentProcessor._process_step
 original_stats=AgentManager.record_environment_stats
 def step(self,step,worker_id,index):
  record(dict(kind="reward",worker=worker_id,agent=int(step.agent_id),reward=float(step.reward),terminal=isinstance(step,TerminalStep)))
  return original_step(self,step,worker_id,index)
 def stats(self,env_stats,worker_id):
  data={k:[float(value) for value,aggregation in values] for k,values in env_stats.items() if k.startswith("__picklebot_diag/")}
  if data:record(dict(kind="metadata",worker=worker_id,data=data))
  return original_stats(self,env_stats,worker_id)
 AgentProcessor._process_step=step
 AgentManager.record_environment_stats=stats
 try:main()
 finally:stream.close()
