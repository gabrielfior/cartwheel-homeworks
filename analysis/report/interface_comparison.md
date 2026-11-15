# Interface comparison

The interface is in `analysis/review_app/` (single-file `index.html`, a standard-library HTTP server in `server.py`, sampling in `sampling.py`, 19 offline tests under `tests/`).

## One design retained from the reference interface

<!-- student:iface_retained -->
I kept three ideas from the supplied reference interface (`analysis/ui/index.html`), re-implemented in `analysis/review_app/` rather than submitted unchanged: a tool call is grouped with the tool result that follows it as one step, the quoted span of a message is highlighted with its margin note beside it, and accepting a suggestion turns it into my own annotation.

I kept them because they keep the evidence for a judgment in one place: the result sits next to the call that produced it, and the note sits next to the sentence it is about, so I do not scroll between a tool result and the reply that describes it.
<!-- /student:iface_retained -->


## One design changed after inspecting my traces

<!-- student:iface_changed -->
I made sure everything from a trace was immediately visible in one single page
<!-- /student:iface_changed -->


## One limitation remaining

<!-- student:iface_limitation -->
It would be better to have a native integration between Langfuse and the new Annotation UI so that data lives in one place
<!-- /student:iface_limitation -->
