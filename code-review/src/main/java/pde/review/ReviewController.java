package pde.review;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** POST /api/review: one Java PR diff in, structured comments out. */
@RestController
public class ReviewController {

    private final ReviewService service = new ReviewService();

    @PostMapping("/api/review")
    public ReviewResult review(@RequestBody Map<String, String> body) {
        return service.review(body.getOrDefault("diff", ""));
    }
}
