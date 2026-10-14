# TalkMoves 模拟学生研究：第一次数据审查

日期：2026-10-14。上游：https://github.com/SumnerLab/TalkMoves 。

审查基准提交：`869b9406de268ebab0f1b9a3bccde0b416b97290`。原始数据与标注未修改，尚未开始训练。

## 结论

可以从这个仓库开始，并优先复用原 TalkMoves 标签。学生回应生成需要从原始课堂文件重新整理对话。原标签描述话语行为，不能直接当成正确性、概念掌握或学习变化标签。补标应针对具体用途所缺的信息，而不是逐句推断心理状态。

上游清洗 notebook 面向分类任务，会去除标点、将学生统一记为 S。这样会影响小数点等数学信息和个体追踪。学生 TSV 的 text_a 也不保证始终为教师发言，因此不能直接作为教师→学生的连续对话生成数据。

## 检查范围

- 成功读取567个原始课堂工作簿：Subset 1为191个，Subset 2为376个。
- 共237,533条至少有一个核心字段内容的数据记录，其中6条没有句子内容。记录数不等于学生数、独立回答数或完整课堂互动数。
- 比较567对原始版与增加 dialogue acts 的版本：565对核心字段完全相同，2对有差异。不能将增加标注的版本当成独立的新课堂重复加入训练。
- 未发现完全相同的整文件核心记录副本；尚未检查全部近似重复和部分重叠。
- 现有训练/测试TSV中，完全相同文本对的交集为学生89对、教师941对。常用短语相同本身不能证明课堂泄漏。
- 原notebook描述了按部分教师/课堂文件隔离测试的策略；我们的生成任务仍需重新核对划分。

这些是全量结构审查结果，不代表逐句完成了教育意义审核。

## 自动警示

| 检查项 | 记录数 | 解释及处理方向 |
|---|---:|---|
| 轮次编号缺失 | 17,019 | 保留行序，不只按Turn拼接。 |
| 带学生标签但身份为S、SS等通用称呼 | 27,189 | 不能把这些记录当作同一个稳定个体。 |
| 教师别名与学生标签同时出现 | 201 | 待核查角色，不代表已确认201个错误。 |
| 教师与学生标注列都有值 | 6,643 | 可能来自合法Context编码，不自动删除。 |
| Sentence单元格不是字符串 | 1,224 | 数值可能是真实数学答案，应保留原值与类型。 |
| 含可能指向图示的词语 | 7,537 | 关键词候选，不能理解为都缺少必要上下文。 |
| 说话者空白 | 73 | 是否能从上下文恢复需核查。 |
| 教师代码超出本次可识别集合 | 10 | 含旧代码6和异常值，保留来源再决定映射。 |
| 学生代码超出本次可识别集合 | 1 | 包含反斜杠等残留，不能作为正常标签。 |

同一记录可触发多个警示，这些数量不能相加作为错误总数。自动警示均未被自动纠正、删除或转化成人工补标。

## 首批十个共同讨论片段

以下全部为待讨论；建议不是已获用户确认的补标。行号均指原始Excel，表头为第1行。`discussion_queue.jsonl`保留各片段原始上下文和标签。

| 编号 | 文件与目标行 | 疑问 | 待讨论建议 |
|---|---|---|---|
| Q001 | Keene.Spring.022020，14–15行；上下文12–50行 | 教师宣布播放视频后出现S和T对白，是否属于录播内容？ | 拟将14–48行作为录播片段待核实，暂不作为现场学生目标。 |
| Q002 | Koski.Spring.012720，54–55行 | Charlie回答false且被标为提供证据，但理由含糊，能否据此判断位值理解？ | 保留原标签；理解状态证据不足。 |
| Q003 | Parker.Spring.010920，44、46行 | Bennett和Adam表达不知道，原标签为none，是否仍可训练？ | 可保留；表达不确定不等于已证明部分掌握。 |
| Q004 | Parker.Spring.010920，247行 | Sadie所指whole和拼块缺少可见信息，能否判断误解？ | 可用话语行为标签；数学判断暂缓。 |
| Q005 | Subset 1 / Math NL4 transcript，182行 | Sentence是数值27，是否属于坏数据？ | 上下文支持其为数学回答；拟转换为文本并保留原类型。 |
| Q006 | Subset 1 / Martino Fraction Equivalence 2_Grade 4，77行 | Speaker是T，却有Student Tag=none，应该归给谁？ | 暂缓作为学生目标，核实来源。 |
| Q007 | Subset 1 / Boats and Fish 2_Grade 4，33、38、45行 | 缺Turn且有Meredith and David联合说话者，如何分轮次？ | 保留行序，联合发言不归为单个稳定学生。 |
| Q008 | Subset 1 / Ribbons 2_Grade 4，354行 | 原始Student Tag为反斜杠，增加dialogue acts的版本为空。 | 固定原始版为主；派生层另记异常和版本差异。 |
| Q009 | Subset 1 / Boats and Fish 1_Grade 4，51、55行 | 学生行同时有Teacher Tag=7 Context和合法Student Tag，是否应删？ | 不因双列都有值而自动删除。 |
| Q010 | Davies.Fall.100319，556行 | 只有Teacher Tag=128，其余核心字段为空，是否属于对话？ | 拟排除生成样本并记录原因，原文件保留；通常无需教育性补标。 |

Subset 2缩写均指对应`TalkBack.Year1.*.xlsx`文件。确切完整路径见讨论清单。

## 首个片段：录播内容与现场回应

原文件：`data/Subset 2/TalkBack.Year1.Keene.Spring.022020.xlsx`。

- 行13，T：I'm going to be teaching you several different ways to find common denominators, we're going to start with a little video to get you guys, your brains into--
- 行14，S：Are those pies for the bake sale? 原Student Tag：1 - none。
- 行15，S：I sure like pie. 原Student Tag：1 - none。
- 行49，T：I want you to take a moment to think, please, and I want you to think what is something I already knew from that video that it reminded me?

前后文本支持中间可能是视频对白，但片段边界仍需确认。这里首先需要补充的是“发言来自哪里、可用于什么”，无需推断学生是否掌握分数。

## 补标与验证原则

原始话语和标签不覆盖。新增说话者来源、针对指定用途的上下文充分性、用途决定、证据行号、理由、标注者与审核状态。理解或变化字段可留空。

不能从一次正确回答推断掌握，不能把“提供理由”解释为理由正确，也不能把教师肯定当作掌握的充分证据。后续纠正可辅助人工判断，但不能泄漏到此前回答的生成输入。

五节已共同阅读的课作为开发资料；最终评价材料另行隔离。人机共同讨论不算独立人工标注者间一致性。

## GitHub进度与复现

完整上游已clone到工作区，GitHub副本已创建：https://github.com/AlexLiu000/TalkMoves 。本次新增的脚本、补标规范与十个待讨论案例位于`research/student_simulation/`；没有修改原始数据和标签。便于共同阅读的完整片段见`DISCUSSION_CASES_ZH.md`，结构化版本见`discussion_queue.jsonl`。

执行`python research/student_simulation/audit.py`可重建结构审查结果，需要openpyxl。原始文件全部成功读取；脚本已通过语法检查。本次尚未训练模型，也未核实全部身份、图示或音视频。
