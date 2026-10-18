-- usmile AI 护齿助手：痛点分析 SQL（SQLite）
-- 数据库：data/processed/usmile.db（由 src/load_db.py 生成，不提交）
-- 运行：.venv/bin/python src/analyze.py   → 结果写到 results/*.csv（只含统计数字，不含评论全文）
--
-- 分析口径（CLAUDE.md 第 5 节、METHODS 第 4 步 D20）：
--   1. 不报告整体好评率（有刷单好评）；中差评是刻意多抽的，比例只在过滤后的样本内有意义。
--   2. 痛点分析排除 generic（空泛/模板好评）。
--   3. 品牌对比尽量在同一来源（source_main）内做。
--   4. info_need（准确率 90%）、ai_can_help（95%）可定量；claim_gap 只做定性，这里不出比例。
--   5. 所有结论只是方向性发现，需用真实业务数据（客服工单、App 搜索词）验证。
--
-- 每段以 “-- name: xxx” 开头，src/analyze.py 按这个标记拆分执行，结果存为 results/xxx.csv。


-- name: 01_sample_overview
-- 样本构成：型号 × 主来源。说明抽样设计，不代表真实好差评比例。
SELECT brand, model,
       SUM(source_main = '最新/普通好评') AS 普通好评,
       SUM(source_main = '追评')          AS 追评,
       SUM(source_main = '中评')          AS 中评,
       SUM(source_main = '差评')          AS 差评,
       COUNT(*)                           AS 合计,
       SUM(generic)                       AS generic条数,
       ROUND(AVG(is_recent_12m), 2)       AS 近12个月占比
FROM reviews
GROUP BY brand, model
ORDER BY is_usmile DESC, brand, model;


-- name: 02_analysis_base
-- 分析样本：排除 generic 后还剩多少条，各来源多少条。
SELECT source_main,
       COUNT(*)                          AS 全部,
       SUM(generic = 0)                  AS 非generic,
       SUM(generic = 1)                  AS generic
FROM reviews
GROUP BY source_main
UNION ALL
SELECT '合计', COUNT(*), SUM(generic = 0), SUM(generic = 1) FROM reviews;


-- name: 03_pain_matrix
-- 痛点矩阵数据（产品标签，非 generic）：
--   提及条数 = 提到该方面的评论数（横轴）
--   负面占比 = 其中情感为负面的比例（纵轴）
--   info_need / ai_can_help 占比 = 提到该方面、且该方面为负面的评论里，标为 true 的比例（气泡颜色）
WITH base AS (
    SELECT t.tag, t.tag_name, t.sentiment, r.review_id, r.info_need, r.ai_can_help
    FROM review_tags t JOIN reviews r USING (review_id)
    WHERE r.generic = 0 AND t.tag_type = '产品'
)
SELECT tag, tag_name,
       COUNT(DISTINCT review_id)                                            AS 提及条数,
       SUM(sentiment = '负面')                                               AS 负面条数,
       ROUND(1.0 * SUM(sentiment = '负面') / COUNT(*), 2)                    AS 负面占比,
       ROUND(1.0 * SUM(sentiment = '负面' AND info_need = 1)
             / NULLIF(SUM(sentiment = '负面'), 0), 2)                        AS 负面中_info_need占比,
       ROUND(1.0 * SUM(sentiment = '负面' AND ai_can_help = 1)
             / NULLIF(SUM(sentiment = '负面'), 0), 2)                        AS 负面中_ai_can_help占比
FROM base
GROUP BY tag, tag_name
ORDER BY 负面条数 DESC, 提及条数 DESC;


-- name: 04_pain_in_negative_reviews
-- 只看中评 + 差评（同一来源内比较，抽样偏差最小）：每个方面被多少条中差评提到为负面。
SELECT t.tag, t.tag_name,
       COUNT(DISTINCT t.review_id) AS 中差评中负面提及,
       ROUND(1.0 * COUNT(DISTINCT t.review_id)
             / (SELECT COUNT(*) FROM reviews WHERE source_main IN ('中评', '差评') AND generic = 0), 2) AS 占中差评比例
FROM review_tags t JOIN reviews r USING (review_id)
WHERE r.source_main IN ('中评', '差评') AND r.generic = 0 AND t.sentiment = '负面'
GROUP BY t.tag, t.tag_name
ORDER BY 中差评中负面提及 DESC;


-- name: 05_non_product_issues
-- 非产品问题（物流、售后、价保、发票、赠品）单独统计，不混进产品痛点。
SELECT t.tag, t.tag_name,
       COUNT(DISTINCT t.review_id)                         AS 提及条数,
       SUM(t.sentiment = '负面')                           AS 负面条数,
       ROUND(1.0 * SUM(t.sentiment = '负面') / COUNT(*), 2) AS 负面占比
FROM review_tags t JOIN reviews r USING (review_id)
WHERE r.generic = 0 AND t.tag_type = '非产品'
GROUP BY t.tag, t.tag_name
ORDER BY 负面条数 DESC;


-- name: 06_ai_opportunity
-- “适合 AI 解决”的比例：在“至少有一个负面标签”的非 generic 评论里，
-- info_need（缺信息导致，严格口径）和 ai_can_help（AI 能缓解，宽口径）各占多少。
WITH pain AS (
    SELECT DISTINCT r.review_id, r.info_need, r.ai_can_help, r.is_usmile
    FROM reviews r JOIN review_tags t USING (review_id)
    WHERE r.generic = 0 AND t.sentiment = '负面'
)
SELECT '全部' AS 范围,
       COUNT(*) AS 有负面反馈的评论,
       SUM(info_need) AS info_need条数, ROUND(AVG(info_need), 2) AS info_need占比,
       SUM(ai_can_help) AS ai_can_help条数, ROUND(AVG(ai_can_help), 2) AS ai_can_help占比
FROM pain
UNION ALL
SELECT CASE is_usmile WHEN 1 THEN 'usmile' ELSE '竞品' END,
       COUNT(*), SUM(info_need), ROUND(AVG(info_need), 2), SUM(ai_can_help), ROUND(AVG(ai_can_help), 2)
FROM pain GROUP BY is_usmile;


-- name: 07_ai_opportunity_product_only
-- 同上，但只看有“产品类负面标签”的评论（排除只抱怨物流、售后、价保的）。
WITH pain AS (
    SELECT DISTINCT r.review_id, r.info_need, r.ai_can_help
    FROM reviews r JOIN review_tags t USING (review_id)
    WHERE r.generic = 0 AND t.sentiment = '负面' AND t.tag_type = '产品'
)
SELECT COUNT(*) AS 有产品负面反馈的评论,
       SUM(info_need) AS info_need条数, ROUND(AVG(info_need), 2) AS info_need占比,
       SUM(ai_can_help) AS ai_can_help条数, ROUND(AVG(ai_can_help), 2) AS ai_can_help占比
FROM pain;


-- name: 08_brand_negative_by_tag
-- 品牌 × 产品方面：中差评里的负面提及条数（同一来源内比较）。
-- 每个品牌的中差评数不同（usmile 3 个型号），同时给出占该品牌中差评的比例。
WITH neg AS (
    SELECT review_id, brand FROM reviews
    WHERE source_main IN ('中评', '差评') AND generic = 0
),
brand_n AS (SELECT brand, COUNT(*) AS n FROM neg GROUP BY brand)
SELECT n.brand, b.n AS 该品牌中差评数, t.tag_name,
       COUNT(DISTINCT t.review_id) AS 负面提及,
       ROUND(1.0 * COUNT(DISTINCT t.review_id) / b.n, 2) AS 占比
FROM neg n
JOIN review_tags t USING (review_id)
JOIN brand_n b USING (brand)
WHERE t.sentiment = '负面' AND t.tag_type = '产品'
GROUP BY n.brand, t.tag_name
ORDER BY n.brand, 负面提及 DESC;


-- name: 09_smart_feature_by_model
-- 智能识别准确度（F7）和 App 与连接（F8）按型号：智能功能是各家高端款的卖点，单独看。
SELECT r.brand, r.model,
       SUM(t.tag = 'F7')                          AS 智能识别_提及,
       SUM(t.tag = 'F7' AND t.sentiment = '负面') AS 智能识别_负面,
       SUM(t.tag = 'F8')                          AS App连接_提及,
       SUM(t.tag = 'F8' AND t.sentiment = '负面') AS App连接_负面,
       ROUND(AVG(r.is_recent_12m), 2)             AS 近12个月占比
FROM reviews r LEFT JOIN review_tags t USING (review_id)
WHERE r.generic = 0
GROUP BY r.brand, r.model
ORDER BY 智能识别_负面 DESC;


-- name: 10_recent_sensitivity
-- 敏感性检查：只用近 12 个月的评论，重算痛点排名，看结论是否被旧评论带偏。
WITH base AS (
    SELECT t.tag, t.tag_name, t.sentiment, r.review_id
    FROM review_tags t JOIN reviews r USING (review_id)
    WHERE r.generic = 0 AND t.tag_type = '产品' AND r.is_recent_12m = 1
)
SELECT tag, tag_name,
       COUNT(DISTINCT review_id)                         AS 近12个月_提及,
       SUM(sentiment = '负面')                           AS 近12个月_负面,
       ROUND(1.0 * SUM(sentiment = '负面') / COUNT(*), 2) AS 近12个月_负面占比
FROM base
GROUP BY tag, tag_name
ORDER BY 近12个月_负面 DESC;


-- name: 11_question_categories
-- 买家提问：主类别分布，以及每类中 AI 能直接回答（info_need）的比例。
SELECT main_category, main_category_name,
       COUNT(*)                  AS 提问数,
       ROUND(1.0 * COUNT(*) / (SELECT COUNT(*) FROM questions), 2) AS 占比,
       SUM(info_need)            AS AI可直接回答,
       ROUND(AVG(info_need), 2)  AS AI可直接回答占比
FROM questions
GROUP BY main_category, main_category_name
ORDER BY 提问数 DESC;


-- name: 12_question_ai_share
-- 买家提问中 AI 能直接回答的总体比例（按品牌）。U7 Pro 只有 2 条提问，样本缺口。
SELECT brand,
       COUNT(*) AS 提问数, SUM(info_need) AS AI可直接回答, ROUND(AVG(info_need), 2) AS 占比
FROM questions GROUP BY brand
UNION ALL
SELECT '合计', COUNT(*), SUM(info_need), ROUND(AVG(info_need), 2) FROM questions;


-- name: 13_evidence_quality
-- 数据质量：标签证据是否为原文子串。
SELECT tag_type, COUNT(*) AS 标签数, SUM(evidence_ok) AS 证据为原文, ROUND(AVG(evidence_ok), 3) AS 比例
FROM review_tags GROUP BY tag_type
UNION ALL
SELECT '合计', COUNT(*), SUM(evidence_ok), ROUND(AVG(evidence_ok), 3) FROM review_tags;


-- name: 14_app_vs_noapp_overview
-- D32：有 App 的 U7 Pro（在笑容加 App 适配列表中）vs 没有 App 的 P10（不在列表中）。
-- 两个型号的样本构成：中差评数、近 12 个月占比（U7 Pro 旧评论多，对比时要注明）。
SELECT model,
       CASE model WHEN 'U7 Pro' THEN '有 App' ELSE '无 App' END AS App支持,
       COUNT(*)                                         AS 全部,
       SUM(generic = 0)                                 AS 非generic,
       SUM(source_main IN ('中评', '差评') AND generic = 0) AS 中差评_非generic,
       ROUND(AVG(is_recent_12m), 2)                     AS 近12个月占比
FROM reviews
WHERE model IN ('U7 Pro', 'P10')
GROUP BY model;


-- name: 15_app_vs_noapp_pain
-- 两个型号各产品方面的负面条数，以及占该型号“有负面反馈评论”的比例。样本很小（每个方面 0–14 条），只看方向。
WITH pain AS (
    SELECT DISTINCT r.review_id, r.model
    FROM reviews r JOIN review_tags t USING (review_id)
    WHERE r.generic = 0 AND t.sentiment = '负面' AND r.model IN ('U7 Pro', 'P10')
),
n AS (SELECT model, COUNT(*) AS 有负面反馈评论 FROM pain GROUP BY model)
SELECT t.tag_name,
       SUM(r.model = 'U7 Pro' AND t.sentiment = '负面') AS U7Pro_负面,
       ROUND(1.0 * SUM(r.model = 'U7 Pro' AND t.sentiment = '负面') / (SELECT 有负面反馈评论 FROM n WHERE model = 'U7 Pro'), 2) AS U7Pro_占比,
       SUM(r.model = 'P10' AND t.sentiment = '负面')    AS P10_负面,
       ROUND(1.0 * SUM(r.model = 'P10' AND t.sentiment = '负面') / (SELECT 有负面反馈评论 FROM n WHERE model = 'P10'), 2) AS P10_占比
FROM review_tags t JOIN reviews r USING (review_id)
WHERE r.generic = 0 AND t.tag_type = '产品' AND r.model IN ('U7 Pro', 'P10')
GROUP BY t.tag_name
ORDER BY U7Pro_负面 + P10_负面 DESC;


-- name: 16_app_vs_noapp_usage
-- 重点：“使用方法与操作”负面，以及有负面反馈的评论中 info_need / ai_can_help 的比例。
WITH pain AS (
    SELECT DISTINCT r.review_id, r.model, r.info_need, r.ai_can_help
    FROM reviews r JOIN review_tags t USING (review_id)
    WHERE r.generic = 0 AND t.sentiment = '负面' AND r.model IN ('U7 Pro', 'P10')
)
SELECT p.model,
       COUNT(*)                                   AS 有负面反馈评论,
       (SELECT COUNT(DISTINCT t.review_id) FROM review_tags t JOIN reviews r USING (review_id)
         WHERE r.model = p.model AND r.generic = 0 AND t.tag = 'F6' AND t.sentiment = '负面') AS 使用方法_负面,
       SUM(info_need)                             AS info_need条数,
       ROUND(AVG(info_need), 2)                   AS info_need占比,
       SUM(ai_can_help)                           AS ai_can_help条数,
       ROUND(AVG(ai_can_help), 2)                 AS ai_can_help占比
FROM pain p
GROUP BY p.model;
