package pde;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

/**
 * 最小示例：把 Prompt 当构件加载和渲染。
 * 模板文件里用 {{key}} 做占位，调用方只传变量，不在代码里拼 Prompt 字符串。
 * 这一步的重点不是调模型，而是让 Prompt 可版本、可测试、可复用。
 */
public class PromptTemplate {
    private final String template;

    public PromptTemplate(String template) {
        this.template = template;
    }

    public static PromptTemplate fromFile(Path path) throws IOException {
        return new PromptTemplate(Files.readString(path));
    }

    public String render(Map<String, String> variables) {
        String result = template;
        for (Map.Entry<String, String> entry : variables.entrySet()) {
            result = result.replace("{{" + entry.getKey() + "}}", entry.getValue());
        }
        return result;
    }
}
