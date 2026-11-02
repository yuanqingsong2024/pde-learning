package pde.review;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Spring Boot entry point for the P3 slice.
 *
 * Production evolution: keep ReviewService's gates (scope, empty,
 * format-only, dedup, severity sort, secret redaction, autoMerge false)
 * and replace each rule lane's findings with Spring AI ChatClient
 * structured output using prompts/pr-review.md. Model calls, keys and
 * prompt templates stay on the backend; the key comes from the
 * SPRING_AI_OPENAI_API_KEY environment variable, never from code.
 */
@SpringBootApplication
public class CodeReviewApplication {

    public static void main(String[] args) {
        SpringApplication.run(CodeReviewApplication.class, args);
    }
}
