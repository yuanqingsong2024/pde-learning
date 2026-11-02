package pde.review;

import java.util.List;

/** Structured review output. autoMerge is always false: merging is human-only. */
public record ReviewResult(String summary, List<ReviewComment> comments,
                           boolean refused, String reason, boolean autoMerge) {
}
