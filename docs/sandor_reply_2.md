# Draft reply to Sándor Beniczky (2)

*Subject: RE: Slowing paper — the two EDFs, and the nomogram idea*

---

Dear Sandor,

Thank you for the files and for checking them so carefully — and for the nomogram suggestion, which I want to
take seriously below.

**The two recordings.** Both read cleanly with our loader: ID-060 gives 61 minutes at 256 Hz and ID-086 four
hours at 500 Hz, and after mapping the modern electrode names (T7/T8/P7/P8) onto our canonical set both yield
a full 19-channel montage with no missing data. You were right that there is nothing wrong with them. The
fault was ours: the failure was on our side of the pipeline, not in your export, and I am sorry we reported
it to you as "unreadable". Your note about ID-060 was still useful — the non-scalp channels are exactly the
kind of thing that would have degraded the read had we not restricted to the scalp array, and we do drop them
automatically. Both are now through the pipeline, and SAI-100 in the revision is n = 100.

I should tell you what that changed, since you would otherwise find it in the next draft. Adding the two recordings moved our focal numbers **down**: one of them is focal-positive by expert majority and LENS does comparatively poorly on it, so focal AUROC goes from 0.938 to 0.930 and the fraction of individual experts falling under our ROC curve from 79% to 64%. The Morgoth gate edges up slightly, SCORE-AI is unchanged, and generalized is unchanged at 0.908. No comparative claim changes, because none of the paired differences was significant to begin with. The completed dataset gives a less flattering number than the truncated one, which is the right reason to prefer it, and I am glad we are reporting the complete set.

**On the nomogram.** I like the idea a great deal, and your reasoning about the reception of AI papers matches
what we have been hearing too. But I should be straightforward about a limitation rather than let it look
easy: **the present paper does not measure the posterior dominant rhythm.** Our features are band powers and
ratios — delta, theta, relative delta, delta/alpha, theta/alpha, and relative alpha — scored per 15-second
segment against age- and sleep-stage-matched norms. No frequency is estimated anywhere in the pipeline. The
PDR appears in the manuscript only as motivation for why an age reference is needed at all.

So a calculator of the form "enter age, get the lower limit of normal PDR frequency" is not something we could
put behind the current results without building a PDR estimator first, and that is genuinely its own piece of
work: the dominant-frequency measures we do have are computed over 1–45 Hz, so in a slow recording they land
on the delta peak rather than the alpha rhythm, which is precisely where a clinician would want the answer to
be trustworthy. It would need eyes-closed wake detection, occipital restriction, an alpha-constrained peak
with a reactivity check, and validation against reported PDR frequencies. Lodder and van Putten, and
Zibrandtsen and Kjaer, each wrote a paper on that problem alone — the ones you sent us, which we have now
cited. We also report in the Limitations that our attempt to recover the *stated* frequency of slowing from
the spectrum failed (rho = 0.13), so we would be adding an unvalidated frequency measure to a paper whose
discipline has been to claim only what it demonstrates.

What we *could* offer in this paper, and what I think would carry much of the clinical usefulness you are
after, is a calculator over the quantities we have actually validated: enter age and sleep stage, and get the
normal range for the deviation features, or enter a recording's values and get its centile and how many SD it
sits from the age- and stage-matched norm. That is exactly what the model already does per segment, it is
calibrated on held-out data (median centile error 1.1 points internally), and it needs no new estimator. It
would also be the first such tool that is sleep-stage-resolved, which is the gap in the existing PDR
literature.

The PDR nomogram itself I would rather do properly as the next paper, using the same normative machinery, and
I would very much like to do it with you if you are interested.

**On the target journal.** Point taken about *Neurology* or *Epilepsia*. I would want to see the revision
settle first — the paired comparisons on SAI-100 turned out not to support the ranking claims we had made, so
the paper is more careful now than it was — but if the age analyses hold up as they have, I agree it is worth
aiming higher.

Thank you again, both for the data and for pushing on this.

Best wishes,
Brandon
