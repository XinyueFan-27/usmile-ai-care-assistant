# 知识库来源清单

> 个人作品集项目，非 usmile 官方。抓取日期均为 2026-10-18（北京时间），之后页面可能变化。
> 来源只用两级：**1 = 品牌官方**（usmile 官网、京东官方自营店商品详情页）；**2 = 权威科普**（国家卫生健康委、中国疾控中心、中华口腔医学会、公立医院医生公开科普）。自媒体、电商软文、第三方下载站、买家评价和“问大家”回答一律不用。
> 长篇原文存档在 `data/processed/kb_raw/`（不提交，见 `kb/README.md`）。

## 1 级：品牌官方

### 京东官方自营店商品详情页

官网“购买渠道”页（S12）列出的线上官方渠道包括“usmile笑容加京东官方自营店”。详情页大多是图片，用本地 OCR（RapidOCR）转文字，再由 Claude 对照原图逐张核对；凡写进 kb/ 的图片内容都已对照原图核对。

| 编号 | 来源 | 链接 | 内容 | 获取方式 |
|---|---|---|---|---|
| S01 | Y30 商品详情页（usmile笑容加京东自营旗舰店） | https://item.jd.com/100215430820.html | 规格参数表（网页文字）；详情图 28 张：模式、续航、刷头更换提醒、App 功能与地区限制、包装清单、售后政策、研发师解答 | 规格表直接读网页；详情图 OCR、已人工核对 |
| S02 | P10 商品详情页（usmile笑容加京东自营旗舰店） | https://item.jd.com/100059598390.html | 规格参数表；详情图 22 张：三档模式、续航、换区提醒、智能褪色刷毛、包装清单、售后政策、研发师解答 | 同上 |
| S03 | U7 Pro 商品详情页（华为京东自营旗舰店，品牌栏显示“鸿蒙智选”） | https://item.jd.com/100216244705.html | 规格参数表；详情图 30 张：识别功能及准确率说明、App、续航、模式、标配刷头、地区与系统限制 | 同上。详情图注明“本产品为第三方商家usmile笑容加品牌提供生产及售后服务” |
| S04 | 京东搜索结果价格快照（只记 usmile笑容加京东自营旗舰店、华为京东自营旗舰店） | https://search.jd.com/ （关键词：usmile笑容加电动牙刷 自营 / F20 / Y50 / 儿童电动牙刷 / 刷头） | 各型号京东价 | 直接读网页。价格随促销变化，只作“价格段”参考 |

### usmile 官网（https://www.usmile.com/cn，广州星际悦动股份有限公司）

| 编号 | 页面 | 链接 | 内容 |
|---|---|---|---|
| S10 | 下载中心（笑容加 App） | https://www.usmile.com/cn/download | App 介绍、iOS / Android 版本要求、适配牙刷列表（页面标注 V4.0.0） |
| S11 | 售后服务 | https://www.usmile.com/cn/aftersale | 防伪验证步骤、保修政策、自助售后、服务热线 |
| S12 | 购买渠道 | https://www.usmile.com/cn/buy | 官方线上商城与线下门店 |
| S13 | 电动牙刷列表 | https://www.usmile.com/cn/electrictoothbrush | 成人电动牙刷系列与型号 |
| S14 | 儿童口腔列表 | https://www.usmile.com/cn/childoralcavity | 儿童电动牙刷型号 |
| S15 | 刷头：灵动® 3.0 刷头 | https://www.usmile.com/cn/accessories/newinfo.html?id=38 | 款式、适配、适用人群、更换周期 |
| S16 | 刷头：第二代类关节缓震刷头 | https://www.usmile.com/cn/accessories/newinfo.html?id=37 | 同上 |
| S17 | 刷头：缓震亮白刷头 | https://www.usmile.com/cn/accessories/info.html?id=1 | 同上，含褪色提醒说明 |
| S18 | 刷头：儿童防蛀刷头系列 | https://www.usmile.com/cn/accessories/newinfo.html?id=36 | 儿童刷头款式、适配、适用年龄、更换周期 |
| S20 | 型号页 Y30 系列 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=30 | 产品参数、与 Y20 对比（含 App 联动） |
| S21 | 型号页 Y30 Pro | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=31 | 产品参数 |
| S22 | 型号页 Y50 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=44 | 产品参数 |
| S23 | 型号页 Y20 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=28 | 产品参数 |
| S24 | 型号页 U7 Pro | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=29 | 产品参数、识别准确率说明 |
| S25 | 型号页 F20 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=33 | 产品参数、专护模式说明 |
| S26 | 型号页 F10 PRO | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=19 | 产品参数 |
| S27 | 型号页 L30 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=42 | 产品参数 |
| S28 | 型号页 P70 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=41 | 产品参数 |
| S29 | 型号页 P20 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=32 | 产品参数 |
| S30 | 型号页 P20 PRO 系列 | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=27 | 产品参数 |
| S31 | 型号页 P10 PRO | https://www.usmile.com/cn/electrictoothbrush/newinfo.html?id=17 | 产品参数、与 P1 / P10 对比 |
| S32 | 型号页 Q30（儿童） | https://www.usmile.com/cn/childoralcavity/newinfo.html?id=35 | 产品参数 |
| S33 | 型号页 Q20Pro（儿童） | https://www.usmile.com/cn/childoralcavity/newinfo.html?id=34 | 产品参数 |
| S34 | 型号页 Q20（儿童） | https://www.usmile.com/cn/childoralcavity/newinfo.html?id=25 | 产品参数 |

官网页面是网页文字，直接读取（`src/kb_fetch_official.py`）。

## 2 级：权威科普

| 编号 | 发布方 | 标题 | 链接 | 日期 |
|---|---|---|---|---|
| A01 | 国家卫生健康委 | 2026 年全国爱牙日重点人群口腔健康核心信息（PDF，4 页） | https://www.nhc.gov.cn/ylyjs/gzdt/202609/a5d831441714460fb70d96791abd0553/files/3.2026%E5%B9%B4%E5%85%A8%E5%9B%BD%E7%88%B1%E7%89%99%E6%97%A5%E9%87%8D%E7%82%B9%E4%BA%BA%E7%BE%A4%E5%8F%A3%E8%85%94%E5%81%A5%E5%BA%B7%E6%A0%B8%E5%BF%83%E4%BF%A1%E6%81%AF.pdf | 2026-09 |
| A02 | 中华口腔医学会 | 世界口腔健康日 2024 核心信息卡（中文版，PDF） | https://www.cndent.com/wp-content/uploads/2024/02/WOHD24-%E6%A0%B8%E5%BF%83%E4%BF%A1%E6%81%AF%E5%8D%A1-%E5%8F%A3%E8%85%94-pb.pdf | 2024 |
| A03 | 中国疾病预防控制中心（慢病中心口腔健康室供稿） | 世界口腔健康日：这些常见误区，可能正在伤害你的牙齿 | https://www.chinacdc.cn/jkkp/mxfcrb/kqjk/202603/t20260323_315840.html | 2026-03-23 |
| A04 | 中国疾病预防控制中心（来源：健康中国） | 龋病、牙龈炎……四类青少年常见口腔问题，如何防治？ | https://www.chinacdc.cn/jkkp/mxfcrb/kqjk/202408/t20240823_295142.html | 2023-06-24 |
| A05 | 健康中国（国家卫生健康委官方新媒体），光明网转载 | 牙龈出血要停止刷牙或用牙线，等待“自愈”……是真是假？ | https://m.gmw.cn/2026-09/24/content_1304567611.htm | 2026-09-24 |
| A06 | 北京市第二医院口腔科主任李培（北京新闻报道，光明网转载） | 今天起，刷牙的方式调整一下！医生：别再“无效刷牙” | https://m.gmw.cn/2026-09/20/content_1304565809.htm | 2026-09-20 |

说明：
- A05、A06 是主流媒体转载，原始发布方分别是国家卫生健康委官方新媒体和公立医院医生，算 2 级；A06 是单个医生的建议，只用于“刷牙方法”的操作细节，与 A03、A04 一致的部分才写成结论。
- 中国疾控中心慢病中心旧版《儿童 / 青少年口腔健康核心信息》PDF 链接已失效（404），未使用。
- 中国牙病防治基金会：本次没有找到可直接读取的相关科普页面【待核实】。

## 没有使用的来源（及原因）

| 来源 | 原因 |
|---|---|
| 第三方 App 下载站、更新日志（如称 4.3.0 新增 Y30、Y30 S、T10） | 第三方，非官方；Y30 已由官方来源确认 |
| 京东“问大家”回答、买家评价 | 买家内容，只用于需求分析（铁律、PRD 第七章“不收录”） |
| 导购网站、自媒体、台湾地区媒体、海外诊所资料 | 不在来源分级内 |
| 京东商品详情“使用说明”标签页 | 是视频，没有文字，本次未转写【待核实】 |
