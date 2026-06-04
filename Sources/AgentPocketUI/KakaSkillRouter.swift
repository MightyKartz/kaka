import AgentPocketCore
import Foundation

public enum KakaSkillRouter {
    public static func route(_ text: String) -> KakaSkillID {
        let value = text.lowercased()
        if value.contains("翻译") || value.contains("translate") {
            return .translateText
        }
        if value.contains("文字") || value.contains("提取") || value.contains("ocr") || value.contains("扫描") {
            return .ocr
        }
        if value.contains("卡路里") || value.contains("热量") || value.contains("calorie") || value.contains("食物") {
            return .nutritionEstimate
        }
        if value.contains("识别")
            || value.contains("这是什么")
            || value.contains("identify")
            || value.contains("植物")
            || value.contains("物体") {
            return .identifySubject
        }
        return .photoEnhance
    }
}
