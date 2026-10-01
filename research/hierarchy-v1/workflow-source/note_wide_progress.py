from pathlib import Path
p=Path(__file__).resolve().parents[1]/'LATEST-STATE.md'
old=p.read_bytes()
text='''# Latest: wide movement comparison COMPLETE; recording retry02 RUNNING

Goal ACTIVE/notcomplete. F:/dev/picklebot feat/hierarchical-control HEAD6fd9131. No training active. Owned Editor39312 PlayMode isolated empty scene Pipeline7800. All4 wide evals COMPLETE512each. Fixture/analyzer completed artifacts/hierarchy-v1/wide-movement-fixture-01. Candidate1048609 A/B legal285/288 overall; axes38/40 out256. A25cm31/64,50cm7/64,75+100cm0/64; directionleft3/66,right0/64,shallow19/62,deep16/64. Familiar247/256. Body moves but contactonly69/256, actualpathmean.439mcontacts/.978mmisses. Widegoalassignmentgain-.00586CIincludeszero. Source5f8c4a10 unchanged. Finalseedsunused.

Recording01 full512finished but Complete() failed sharingviolation before writingposes/parity. error.json/images preserved. retry_wide_recording.py RAN, newoutputs/wide-movement-review-02 same7seeds/512recipe, only terminalwriterclosurefix. capture.csSHAfb321c89fe5b31184aa9d4ef64f2b1532e3679e0fbd53d3adf31810830b5dd54 registeredasync SUCCESS. Wait02complete/error; nofunctions/shellsessionpending. Do NOT rerunselector/retry/capture; framesneedtruecomplete+parity. build_wide_recording.py --output-namewide-movement-review-02 AFTERcomplete; mustUIinspectbrowserexistingagent/browserpersistentbindings. Browserdocs+localdevread. audit_placement_analysispreparingarchiver supporting02+01failure; noFwrites. Capturesource unchanged until allvalidation/archive done.

Rootarchive_wide_movement.py ready NOTRUN, requires ownedEditorstop+wide-restore_editor.cs closes39312/restoredmarker thenverifyexit/logstable. Outputdocs/research/execution-v1-evidence/wide-movement-01 and research/hierarchy-v1/wide-movement-01. Reportuntracked docs/research/execution-v1-wide-movement.md exists. update_wide_docs.py READYNOTRUN, updatescurrent+goal/hierarchy/coverage preservinghistoricalbytes. Thenlocalcommit(no push).

NEXTtrain: opt-inaxesrecoveryfocus. Runtimepatch workspace axes-recovery-opt-in.patch SHA310f3c34864ffc824eed72367327ab5fb5c733723ec5d2a95f60dc12882ed86c NOTAPPLIED. Changes RecoverySchedule.For optionalfocusPattern + Recoverycaller+Validate. Defaultlateralunchanged. Focusaxes .0625 gives6.25–25cm; mix25/25/50same/prior.1/interleavingsame. review_two_regionsprepares testcleanup+NEWsource/build+fullAdamresume launcher/setup campaignaxes-recovery-01/runexecution-axes-recovery-01 target2097152,8x16. Do NOTuseunchangedprepare_execution_2m.py draft/oldbuild. Need tests/build/plan before launch. Samecurrent1048609fullcheckpoint; boundedendpoint+oldnarrow/wideevaluation.

TensorBoard22436(6009),README2860(6010)preserve. No blockers/fullgoalunfinished.

---
'''
p.write_bytes(text.encode()+old)
print('Latest workspace handoff updated')
