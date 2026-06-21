# 作業ログ (work_log)

## 2026-06-20 — 設計デッキ統合（重複解消）＋①サマリーのファネル数値を実データ確認

- ダッシュボード設計PDFの重複を解消。1枚物 summary_revised_fixed.pdf と ChatGPT版 osaka_real_estate_dashboard_revised.pdf でサマリーが重複していたため、SUMMARY→EVIDENCE→ACTION の3枚デッキに統合（scripts/make_storyboard.py）。①=改良サマリー、②=見どころ①②の実証（C vs F比較表＋区別バイアス＋逆選択）、③=見どころ③＝限界明示＋本命駅＋次の一手。空き家だった旧②③（各1行）を実質化。重複していた1枚物PDF/PNGは削除（make_summary_revised.pyで再生成可）。dashboard_mockups.pdf（実チャートのモック）は役割違いで併存。
- ①サマリーTableau化に向け、ファネル数値を実データで確認（scripts/confirm_funnel.py・confirm_honmei.py／読み取り専用）。
  - mart_condo_price(2025/fold A test): 取引2,106件・取引のあった駅155・相場比較可能(model_eligible)151駅・10件以上66駅。**サマリー表記2,097件は古く実データは2,106件**→デッキPDF修正。
  - mart_opportunity_list: 66駅/stable20/本命10（本命=stable_flag AND high_risk_share<0.10）。priority_score上位5=堺筋本町80.8/玉造79.3/平野79.1(要確認・旧耐震×改装不明0.857)/大国町77.8/松屋町74.3。本命10駅=堺筋本町・玉造・大国町・松屋町・中之島・森ノ宮・谷町四丁目・桜ノ宮・伝法・淀屋橋。平野はbalance3位だがrank_risk33・high_risk0.857で★本命除外＝▲要確認（設計どおり）。
- ①サマリーは Option①（martを別々の単一接続で繋ぎ動的算出）で確定。DS1=mart_opportunity_list（本命/要確認バー・66/10）、DS2=mart_condo_price（ファネル2,106/151）。計算フィールド: 判定区分・本命駅数・比較可能な駅数。
- 次: Tableauで①サマリーを実装（KPI4タイル＋本命/要確認上位10バー＋見どころ/限界テキスト）。

## 2026-06-18 — 画面4補強 区別バイアステーブル（model_bias_by_ward）＋interview_notes追記

- 「Fがなぜ却下か」を視覚証明するため osaka_real_estate.model_bias_by_ward 作成（sql/bqml/06_bias_by_ward.sql・実測materialize）。区×モデル(C/F)×signed_bias、取引20件以上の20区。
- 結果: F−C が全20区でほぼ+0.12〜0.18の一定＝Fは一律の値上がり補正を足すだけ。C時点で各区ズレが違う(中心-0.19〜周縁+0.20)ため、一律加算で中心は0に改善も周縁が+0.27〜0.39に膨張（住吉+0.20→+0.39/平野+0.15→+0.33）。Fは平均を直すが区ごとのバラつき(順位を歪める元)は直さない＝精度改善≠ランキング改善を数値で証明。
- interview_notes 追記: 「駅×年トレンドで精緻化しない理由」(循環で割安シグナル消失・データ希薄・既に駅相対乖離で対処／精度↑が目的を壊す境界)。
- 次: Tableauで区別バイアス比較グラフ(画面4補強)→採用理由ラベル→画面0サマリー→ダッシュボード→再公開。

## 2026-06-18 — 画面4用 モデル評価テーブル作成（model_eval_metrics）

- Tableau画面4(モデル評価)用に osaka_real_estate.model_eval_metrics を作成（sql/bqml/05_eval_metrics_table.sql）。
- **当初ハードコード版を書きかけたがユーザー指摘で実測materialize版に修正**（再現性・監査性）。02_evaluate.sql ブロック1と同一ロジックを CREATE TABLE 化。ML.PREDICTの実測から算出。
- 検証: 値がフェーズ2記録と完全一致（Baseline hit10 0.176/Model C 0.269・MAE12.1万・bias-0.093/Model F 0.329・MAE10.1万）。7モデル×指標(hit10/hit20/mdape/mae/rmse/signed_bias)+adopted/ord列。
- 教訓: 評価指標も手打ちせず実モデルから焼く（predictions_model_cと同思想・dbt外の手動BQMLステップ）。
- 残宿題: Tableauブック保存・完成時の再公開・実行順序README(Step14)・本変更のコミット。
- 次: Tableauで画面4(評価棒グラフ)→画面0(サマリー+方法論)→ダッシュボード組み立て。

## 2026-06-18 — Tableau検証中の指摘からスコア修正（D-033・A案）

- ユーザーが「リスク重視にしても旧耐震86%の平野が上位＝矛盾」と指摘。リスク高率は固定値で配点と無関係だが、根本はC案で旧耐震をスコアに入れていなかったためリスク重視が最大リスクを無視していた。
- A案採用(D-033): リスク重視モードのみ score_risk に -30×high_risk_share を追加。バランス/割安重視はC案維持。dbt run PASS。
- 効果: 平野 リスク重視2位→33位(割安重視は1位維持)。リスク重視Top5は旧耐震0〜12%のクリーン駅。「最も安いが最も危険」が配点切替で物語化。
- 要対応: TableauはBigQuery抽出のため、ユーザー側で抽出を更新して新スコアを反映する必要あり。

## 2026-06-17 — Step 13: Tableau ダッシュボード設計（仕様書）

- Tableau準備の健全性チェック合格: 緯度経度66駅NULL/ゼロ/府外=0、感度分析新列NULL0・スコア0-100内、building_risk_label「その他」=0(フラグ整合)、物件2097件のラベル/乖離/予測NULL0。データはクリーンで修正不要。
- docs/tableau_design.md 作成（3画面：①駅マップ ②駅詳細drill ③候補比較表）。データソースA=mart_opportunity_list(66駅)/B=int_property_deviation(2097物件)をstation_nameでリレーション。配点パターンのパラメーター＋計算フィールドで3配点切替。設計原則=割安を単独で見せず high_risk_share/stable_flag を並置・「調査候補/現物確認前提」を全画面注記。
- Tableau Desktop での組み立てはユーザー作業（GUI）。私はデータ準備＋仕様書を担当。
- 次: ユーザーがTableau構築→tableau/screenshots/ に保存→Step 14（README/物語化・実行順序明記・GitHub公開）。

## 2026-06-16 — 手順書 PART 15/17 整合（D-032）

- 監査でPART15/17の未反映を検出→整合。dbt run PASS=2 / test PASS=11。
- **C案（D-032a）**: 旧耐震を減点でなく可視化。int に building_risk_label、mart に old_seismic_share/high_risk_share 追加。平野 high_risk_share=0.857（割安だが要注意）/玉造・大国町=0.0 が数字化。二重計上回避と15-A整合を両立。
- **17-3 感度分析（D-032b）**: 3配点（バランス/割安重視/リスク重視）でスコア化＋stable_flag(3中2回以上Top20)。mart を「素のパーセンタイルに配点を掛ける」構造に再設計。主スコアはバランス型で従来と同値(±0.1丸め差)。実測: 安定候補20駅・上位10は全安定・難波(9→割安重視23)等が配点で動く。
- **15-6 係数（D-032c）**: sql/bqml/04_inspect_weights.sql で ML.WEIGHTS確認。築年-0.32(支配)・駅中央値+0.17・徒歩-0.04(手順書どおり)・改装+0.016/新耐震-0.005(ほぼ無力)。符号を実係数で説明可。
- 改装不明は品質に戻さない（D-029維持・94%欠損）。
- 次: 本変更のコミット → Step 13 Tableau（感度パターンフィルタ・安定候補・リスク理由列＝17-4の素材が揃った）。

## 2026-06-16 — パイプライン全体監査と清掃（D-031）

- 取得→絞り込み→外れ値→欠損→特徴量→モデル→検証→スコアをデータで監査。結果を壊すバグ無し。
- 実測で確認: 絞り込み漏斗 24,613→7,912(32%)・除外の91%(15,245)が面積帯外＝対象は20-60㎡帯のみ。outlier_pps_flag=price_per_sqm<50000(stg:64)で価格下限500万と冗長＝スコープ恒久0(実測0/2097)。改装陽性3.9%。2025補完率 築0.1/徒歩1.5/地価0%。極端高値400万/㎡(訓練)・200万(2025・29件)が無印素通り。カバレッジ66/151駅(44%)だが取引では84%。割安under_level 66駅中31負・中央値+0.02の相対指標。
- 清掃: **outlier_pps_flag をリスクから除去**（恒久0の飾り）→mart再ビルドでスコア完全不変を確認(堺筋本町80.8等)。test PASS=5。
- 文書化: D-031(a〜f)。brief 1節を「20-60㎡帯」に修正＋4.6節に監査限界を追記。interview_notes に自分から言える弱点4点を追記。
- 改装はモデルから外さず明記（再カスケード回避・効果ゼロ）。中心的限界=割安は「下振れ」で好機/衰退を判別不能、Step12検証が切り分け。
- 次: 清掃分のコミット → Step 13 Tableau。

## 2026-06-16 — Step 12: 上位駅の目視検証（データ駆動の逆選択スクリーニング）

- 上位10駅をデータ検証のみで裏取り（外部サイト目視なし・現物確認は人へ）。docs/verification_notes.md 作成。
- 逆選択の指紋（旧耐震率・大型偏り・築年・極端外れ値の集中・乖離の一様性）で3分類:
  - ①本物っぽい割安: 堺筋本町/玉造/大国町/森ノ宮（新しめ築年・旧耐震ほぼ0・分布一様）
  - ②逆選択濃厚: 平野（旧耐震86%・大型95%・築52年＝老朽大型の集中）
  - ③要現物確認: 松屋町(-70%の1物件牽引)/中之島(高額大型の個別)/谷町四丁目/桜ノ宮(薄12件)/難波(under_level+0.04でそもそも割安でない)
- **横断発見**: 極端割安個票(駅相対-30〜-70%)はほぼ全て outlier_pps_flag=0＝既存の絶対IQR外れ値フラグをすり抜ける（駅相対で異常な物件）。松屋町-70%が無印。→現物確認必須＋将来「駅相対外れ値フラグ」を提案。
- **ビジネスインパクト確定**: 2,097件/151駅→上位10駅(309件=全駅7%)に圧縮、割安プール472件(22.5%)抽出、上位10駅は約4駅本物/1駅逆選択/残り要確認＝正しく仕分け。brief 6節に反映。
- 面接対策: docs/interview_notes.md 作成（3大アピールの想定問答）。平野の記述を精密版に修正＝「老朽だから安い」(モデルが築年織込済で論理破綻)を避け「割安シグナルが最も不確実なセグメントに集中→リスク仕分けで降格」に言い換え（verification_notes も同様修正）。
- 次: Step 13 Tableau（地図で駅別割安度→駅選択で物件分布の2階構造）。または Step 12成果のコミット。

## 2026-06-16 — Step 11 スコア解剖と品質軸の修正（D-029/D-030）

- スコア完成後に各軸のばらつき・相関を実測し、35点ぶん（品質15・リスク20）がほぼ死んでいると判明（sc_quality sd0.9/corr0.01・risk中央0/corr0.11。割安sd13.3/corr0.81・信頼sd5.1/corr0.44は健全・地価はsd4.4だがcorr0.03で割安と無相関）。
- **D-029で品質軸を修正**: 改装不明(94%欠損=データ収集の癖)を品質から除外し補完フラグのみに。再ビルド結果: sc_quality 中央0.4→15.0、**偽の66点天井が消えスコア範囲24.7〜80.8に正常化**。上位は1堺筋本町2玉造3平野4大国町と不変＝割安主導の構造は維持。
- 正直な限界: 補完は全駅で稀なため品質は依然ほぼ定数+15（sd0.5）。順位を動かさないのはバグでなくデータの現実（駅間で完全性に差なし）。無い差を捏造せず明記。
- **D-030**: リスクは旧耐震単独に広げない（価格に織込済で二重計上回避）・現状は安全弁と位置づけ。地価はcorr0.03でプレミアム度の別軸として仕様どおり残し明記。
- 次: Step 11成果(フェーズ3-5)をコミット→Step 12 上位駅の目視検証。

## 2026-06-16 — Step 11 フェーズ5: 調査優先度ランキング（mart_opportunity_list・本命成果物）

- mart_opportunity_list（marts table・66駅）作成。2025年10件以上の駅を 割安45+信頼25+地価15+品質15−リスク20 でスコア化（D-027/D-028・全要素パーセンタイル/比率）。dbt run PASS=1 / test PASS=5。
- 失敗と修正: 型混在でエラー2回。is_negative_age/outlier_pps_flag/renovation_*_flag/seismic_old_flag=INT64、potential_dup_flag/is_imputed_*=BOOL。OR条件で INT64は=1・BOOLは直接に統一して解消。sc_reliabilityの小数ノイズはROUND整形。
- **設計妥当性を実データで検証（着手前の懸念①②）**:
  - 懸念①「45/55構造で割安が薄まる」→ **杞憂。corr(priority_score, 割安度)=0.766**、上位15駅中14駅が割安(under_level<0)・割高0。割安が順位を主導。
  - 懸念②「割高な人気エリアが上位に紛れる」→ **0件**（under_level>0.05かつ上位20は無し）。
  - 残る軽微caveat: 難波(10位・under_level+0.04)は信頼性20.8+地価14.8で上位＝厚みと地価で乗った例。伝法(最割安-0.40だが薄さ・低地価で9位)＝配点トレードオフが意図どおり機能。
- 上位: 1堺筋本町 2玉造 3平野 4大国町 5松屋町。平野はbargain_share0.43と高く周縁＝逆選択ウォッチ（Step12目視対象）。
- 次: Step 12（上位駅の目視検証＝なぜ安いかの裏取り・逆選択チェック）。brief 6節のビジネスインパクト数値（圧縮率）を埋める。

## 2026-06-16 — Step 11 フェーズ4: 駅相対乖離（int_property_deviation・二段補正 D-026）

- predictions_model_c を dbt source 登録 → int_property_deviation（intermediate view）作成。二段加法補正: 乖離率−市全体の面積帯中央値−駅内中央値。中央値はPERCENTILE_CONT分析関数。schema.yml全カラム日本語description付与。dbt run PASS=1 / test PASS=5。
- 検証: **二段補正が機能**。面積帯別 raw中央値 +0.09〜+0.17（過小バイアスの帯差）→帯補正後ほぼ0（-0.001〜-0.011）→最終もほぼ0。駅内中央値は66駅(10件以上)で中央値0に集約。
- **新発見（フェーズ5への申し送り）**: 最終割安トップ8が全て45〜60㎡帯で旧耐震が多い（都島/福島/東淀川/蒲生四丁目 築39〜57年、松屋町中央区 raw-59%）。理由 ①逆選択(築古大型=再建築不可/管理不良の典型)②二段補正は帯の中央値=位置は揃えたが分散=スケールは揃えていないため大型帯に極端な負値が集中。→ 割安度を乖離の大きさでそのまま点数化すると上位が大型・築古に偏る。**対処: 割安度はパーセンタイル/順位で点数化（分散差を自然吸収・推奨）または帯内スケール正規化。フェーズ5で確定。**
- 次: フェーズ5（調査優先度スコア=割安45+信頼25+地価15+品質15−リスク20、0-100クリップ）→駅集約 mart_opportunity_list。割安度の点数化方式を先に決める。

## 2026-06-16 — Step 10 フェーズ3: 予測生成（predictions_model_c 作成）

- sql/bqml/03_predict.sql 実行（scripts/predict.py）。Model C で予測㎡単価を生成し新規テーブル osaka_real_estate.predictions_model_c に焼いた（候補=2025年・fold A test）。
- 検証: **2,097件・151駅・予測/実勢NULL=0**・予測範囲15.3万〜137万円/㎡（常識的）・smearing係数1.029（log残差ほぼ対称）。
- **全体バイアス 平均-9.3%/中央-13.6% ＝ フェーズ2 Model C(-9.3%)と一致**＝予測の再現性確認。この過小予測は次フェーズの駅相対乖離（駅内中央値引き）で相殺する（D-023）。
- **逆選択が実データで顕在化**: 額面で最も割安な上位は松屋町(中央区55㎡ 実勢21.8万 vs 予測53.7万 −59%)・千林(−59%)・我孫子町(−57%)等。中央区で予測半額以下＝ほぼ確実に事故物件/借地権/再建築不可/劣化/データ誤り。**物件単位の額面ランキングを信じない（D-024/D-025）主張を自プロジェクトで実証**＝面接の実例。
- 次: フェーズ4（駅相対乖離＝物件の予測残差を駅内で正規化）→駅集約。セグメント混在対策（面積帯別の要否・D-025(3)）はフェーズ4着手時に確定。

## 2026-06-16 — Step 11 着手前レビュー：成果物の軸を駅単位へ（D-024/D-025）

- 8年目アナリスト視点のレビューで重大論点を2つ検出し設計を修正。
  - **①データ用途のミスマッチ**: 成約価格情報＝売れ終わった取引で売出リストでない→個別2025物件は買えない＝非アクショナブル。**②逆選択**: 相場より安い物件はデータに写らない瑕疵（事故物件・再建築不可・1階北向き・管理不良）で安いことが多く乖離トップは地雷に偏る。
  - 対応 **D-024**: 本命成果物を「駅・エリア単位の割安傾向＝仕入れ優先エリア」に格上げ、物件単位は手法デモ＋可視化に降格。**D-025**: 最低件数しきい値/逆選択は駅集約＋リスク減点＋要確認明記/セグメント混在は面積帯別検討/配点は感度分析。
  - project_brief.md に 4.5節（データ用途の限界と成果物の軸）追加、5節（成果物）を駅主軸に再定義。
- フェーズ3の03_predict.sql（Model Cで予測を焼く）は土台として不変（駅集約にも必要）。対象=2025年（fold='A' split='test' model_eligible・2,097件）で確定。
- 次: 03_predict.sql レビュー→承認後に実行。

## 2026-06-16 — プロジェクト・ブリーフ作成（軸の明文化）

- docs/project_brief.md を作成。以降の判断の軸＝面接の台本。ビジネス課題（仕入れ一次スクリーニングの工数圧縮）・立て付け（査定でなくスクリーナー／絶対精度でなく駅内相対順位）・精度の正直な現状・芯になる判断（D-022 F却下/D-023 駅相対）・成果物4点・ビジネスインパクトの言い方・「自社データなら何ができるか」・残りロードマップ(Step11-14)を1枚に集約。
- 方針: これ以上モデル精度を追わない（データ由来の下限を実証済み）。残り工数は「使える成果物」に全振り。GA technologies(RENOSY)の仕入れ実務に重ねた立て付けにする。
- 次: Step 11（割安候補リスト作成＝フェーズ3 予測生成→駅相対乖離→調査優先度スコア）。

## 2026-06-16 — Step 10 フェーズ2: モデル評価・比較（branch: feature/step10-model）

- sql/bqml/02_evaluate.sql 作成（4ブロック・読み取りのみ）＋ scripts/evaluate_models.py で実行。Fold A・テスト2025（n=2,097）・model_eligible。log逆変換は Duan smearing 係数（訓練残差）で補正。主指標=±10%以内的中率(hit10)。
- 事前レビューで02_evaluate.sqlの欠陥1件を修正: キャリブレーション倍率を `AVG(actual/pred)`（比の平均・低価格側に歪む）→ `SUM(actual)/SUM(pred)`（平均の比）＋中央比を併記。
- **比較表（hit10 / hit20 / MdAPE / MAE円per㎡ / 符号付バイアス平均）**:
  - Baseline(駅中央値) 0.176 / 0.356 / 0.286 / 186,117 / -0.040
  - Model A(面積+築年+徒歩) 0.267 / 0.486 / 0.209 / 135,409 / -0.067
  - Model B(A+改装+新耐震) 0.269 / 0.482 / 0.209 / 135,611 / -0.067
  - **Model C(B+駅中央値) 0.269 / 0.540 / 0.183 / 120,567 / -0.093**
  - Model D(C+公示価格) 0.269 / 0.537 / 0.188 / 120,655 / -0.095 ＝Cと同等
  - Model E_tree(BOOSTED) 0.269 / 0.535 / 0.186 / 123,853 / -0.089 ＝Cと同等(MAEは悪化)
  - Model F_time(C+時点index) 0.329 / 0.586 / 0.161 / 101,093 / +0.042
- **主要所見**:
  1. Baseline→Cで実質改善（MAE 18.6万→12.1万・MdAPE 0.286→0.183）。駅中央値(C)が効く。
  2. **D（公示価格）はCと同等＝予測に効かない→v9方針を実測で支持**（narrative=二重カウント回避でスコア側へ）。
  3. **E_tree もCと同等（MAEむしろ悪化）＝木で取りこぼし無し→線形で十分**。
  4. Cは2025を-9〜13%過小予測（フェーズ0予想6-7%より大）。
  5. **【最重要】Model F_time は全指標で最良だが採用不可**。残差を区別に割ると、全市共通の単一時点傾きで底上げした結果、空間構造バイアスを悪化させた（周縁・割安区を過大予測：平野 C+0.15→F+0.33、住吉 C+0.20→F+0.39、此花/住之江/東住吉 +0.26〜0.28）。築古も過大（40年+ +0.09）。過大予測=実勢が予測より安く見える=「割安候補」の誤検出。割安抽出ツールにとって一次の欠陥。
  6. Fold A/B 安定性（Model C）: Fold A(テスト2025) hit10 0.269/バイアス-0.093、Fold B(テスト2024) hit10 0.318/バイアス-0.064。外挿が短いFold Bが良い＝バイアスは予測地平に比例＝値上がり説と整合。大崩れなし。
  7. 残差診断: 面積帯は小型(20-30㎡)が最良(hit10 0.36)・大型(50-60㎡)が最差(0.21)＝事前に懸念した「小型が誤差床」は逆。築年帯は新築側ほど過小、築古ほど中立。
- **教訓**: 一様バイアスは順位を保つが構造化バイアスは順位を歪める。MAEが良い≠スクリーニングに良い。
- **推奨（未確定・要承認）**: 採用=Model C。D/E不採用（実測で根拠化）。時点バイアスは(b)スカラー/(c)時点項では空間構造が残る/悪化するため不採用。代わりに割安乖離を「物件 vs その駅相場」で相対測定し一様な時点・駅固定レベルを相殺（(a)の精緻版・プロジェクト方針と一致）。
- 次: 採用判断の承認→decision_log確定→フェーズ3（採用モデルで predicted_price_per_sqm 生成）。

## 2026-06-15 — Step 10 フェーズ1: BQMLモデル作成（branch: feature/step10-model）

- sql/bqml/01_create_models.sql で7モデル作成（Baselineはevaluate側でSQL計算のため除く）。osaka_real_estate データセット。
  - 線形: model_a/b/c/d、model_f_time(C+時点index=trade_year-2021)、model_c_foldb（Fold B・安定性）。l2_reg=0.01・NO_SPLIT・log_price_per_sqm。
  - 木: model_e_tree（BOOSTED_TREE・max_iter=30）。学習が長く(約8分超)、Pythonクライアントのタイムアウト後もBQ側ジョブは継続して完了。
- 学習損失（logスケール・訓練・方向性のみ）: A0.0762 / B0.0758 / C0.0545 / D0.0535 / F0.0504 / C_foldB0.0488 / E_tree0.574(別尺度)。
  - 早期所見: 駅中央値(C)で大改善・公示価格(D)はわずか(v9支持)・時点項(F)で改善(値上がり整合)。**公平な比較はフェーズ2**。
- 注意点: 木モデルの損失は線形と非可比でフェーズ2で要検証。出力バッファ対策に python -u を使用。
- 実行: Python BQクライアント（gcloud回避策）。次はフェーズ2（評価・比較）。

## 2026-06-15 — Step 10 フェーズ0: 価格モデル前の診断（読み取り専用）

- sql/bqml/00_pre_checks.sql を作成し13種の診断を実行（Python BQクライアント・SELECTのみ・BQ書き込みなし）。詳細結果は docs/step10_model_plan.md 4.5節。
- 主要結論:
  - 報告ラグ無し→テスト2025通年。log変換は妥当（歪度1.76→-0.18）。
  - 値上がりが実在（面積帯・主要駅を固定しても+25〜29%/2021-2025、訓練駅中央値vs2025実績で+6.5%）→ モデルは2025を約6-7%低く予測する系統バイアス→時点補正が必要。
  - **重要発見**: corr(駅中央値,公示価格)=0.40のみ。v9の「公示価格は駅相場と重複」前提は事前には弱く、Model Dは決め打ちせず実測する（narrativeを二重カウント回避の設計判断に修正）。
  - 築年は非線形で支配的(相関-0.81)→木モデル比較の価値。外れ値pps=0(scope除外済)。駅別訓練件数は54%の駅が20件未満。
- フェーズ1着手前の確定: テスト2025通年/log採用/時点補正要(残差→キャリブレーション)/木モデル作成/Model D実測/外れ値対応不要。
- 失敗と修正: 診断SQLで COUNTIF(INT64列) エラー→ =1 比較に修正。preamble中の区切り文字列を回避。

## 2026-06-15 — Step 10 事前レビュー（モデル設計の懸念点と対策を文書化）

- 実装前に、予測㎡単価モデル計画を実務レビュー。7つの懸念点（①市場値上がり未反映 ②ログ逆変換の下振れ ③面積5㎡丸め×小型 ④駅中央値の循環性 ⑤MAPE偏重 ⑥線形の取りこぼし ⑦2025報告ラグ）と各対策を `docs/step10_model_plan.md` に記録。
- 方針: 精度追求より「弱点を明示し相対ランキングの頑健性を主張」。測ってから設計を決める（フェーズ0診断→1作成→2評価→3予測）。
- 未実装（SQLはまだ作成していない）。次はフェーズ0（2025四半期件数・年次値上がり率・面積帯件数）から。

## 2026-06-15 — Step 9: mart_condo_price 構築（分析完成テーブル）

- mart_condo_price（materialized: table・13,718行=両Fold）作成。intermediate を整形し正規の列名で公開。
  - 予測特徴量は補完済みの値を正規名（building_age_years/walk_minutes）で公開、スコア用項目（公示価格・駅件数/IQR・renovation_unknown・seismic_old_flag）は分離（v9核心）
  - 両Fold保持＋fold/split列（Tableauはfold='A'。PART17のFold横断比較対応）
  - 目的変数 log_price_per_sqm を追加（BQML用）
- staging小修正: stg_transactions に potential_dup_flag を追加（D-005の実装漏れを補完。Fold A 182件）
- D-017反映: 新規出現駅（駅中央値NULL）は station_history_missing=TRUE / model_eligible=FALSE で識別し、モデル・予測・ランキングから除外（martには残す）。Fold A test 9件・Fold B test 8件
- 検証: **model_eligible行 13,701件で予測特徴量NULL=0**・log_price_per_sqm NULL=0・Fold/split件数整合（A:5,806+2,106 / B:4,201+1,605）
- 失敗と修正: mart で trade_price 列名誤り→ stg の列名 price に修正
- dbt run PASS=8 / dbt test 実行
- 次: Step 10 モデル（中央値ベースライン + BQML、PART17のBaseline〜Model D比較・Fold A本番/Fold B検証）

## 2026-06-15 — 整合性監査と耐震フラグの矛盾修正

- 目的（割安候補抽出＋スコアリング）に対しデータ補正が一貫しているか監査。最終テーブル46列を確認し、予測特徴量とスコア用項目の分離・リーク防止・層構造・限界明示が一貫していることを確認。
- 検出した唯一の論理矛盾: 耐震フラグの二重定義（補完で旧耐震化した9行が seismic_new=0 かつ seismic_old_flag=0）。
- 修正（D-020）: seismic_old_flag を staging から削除し、intermediate で seismic_new と相補的に補完後築年から算出。検証で矛盾0行（seismic_new+seismic_old_flag=1）、補完由来の旧耐震18行は is_imputed_building_age で区別可能。dbt run PASS=7 / dbt test PASS=21。
- 軽微: D-011 本文に実装後の数値（scope7,912/complete-case7,796/126駅）の注記を追加。
- 残課題（Step 9へ）: D-017 新規出現駅の駅中央値NULL（A:9/B:8）の扱い。モデルは imputed_* と seismic_new/seismic_old_flag を使う。

## 2026-06-15 — Step 8: 欠損値の補完（Fold対応・リーク防止・列ごとに理由のある方法）

- 方針（D-018/D-019）: 一律中央値でなく列ごとに最適な方法。補完中央値は当該Foldの訓練期間のみから算出（PERCENTILE_CONT(IF(split='train',...))）。
  - 築年数: 駅→区→全体の中央値 + is_imputed_building_age（欠損は全て真の不明＝戦前0件を確認）
  - 徒歩分: 駅→区の中央値 + is_imputed_walk_minutes（駅×面積帯は根拠薄で不採用）
  - 公示価格: int_station_land_price_features の対象を全取引駅に拡大し実計算（4駅の欠損解消）。補完は座標無し時のみ（実績0）
  - seismic_new を補完後築年数から再計算
- stg_transactions: scope を「徒歩・築年の欠損は駅があれば対象に含め補完／駅名欠損は除外（station_missing）」に変更
  - 不具合検出と修正: 当初 scope を欠損許容にしたら駅名空欄314行が混入し駅中央値・地価がNULLに → 駅名必須化で解消（D-019・errors_and_fixes）
- 検証（scripts/verify_intermediate.py + アドホック）:
  - scope_true=**7,912**（complete-case 7,796 + 補完対象116）・駅名空欄の混入0
  - 駅結合率 **100%**・補完後の築年/徒歩NULL=0・地価補完0（全て実値）
  - 補完値は範囲内（築5-58年・徒歩1-20分）・補完件数 築56/徒歩60
  - 駅中央値NULL（新規出現駅）Fold A test9/Fold B test8（D-017・要Step9対応）
- **dbt run PASS=7 / dbt test PASS=21**（補完列のnot_null 4件追加）
- 次: Step 9 mart。D-017（テスト期間の駅中央値NULL）の扱いを決める

## 2026-06-15 — Step 8: intermediate 構築（駅特徴量・地価特徴量・物件結合）

- 作成モデル（dbt/models/intermediate/・全 view）:
  - `int_station_geo`: 駅名→代表座標・代表路線。大阪府bbox限定で同名駅の全国平均ズレを防ぐ共通テーブル（D-016）
  - `int_station_market_features`（駅×Fold）: 取引件数・中央値㎡単価・IQR・平均徒歩・改装率を各Foldの訓練期間のみで算出（D-012=D-009の具体化）
  - `int_station_land_price_features`（駅）: 最寄り公示価格・対前年変動率・距離を ST_DISTANCE 最近傍結合
  - `int_transactions_with_station_features`（物件×Fold）: 上記を結合した mart/BQML 用の行レベルテーブル
- 前提整備（staging補修）: マクロ `normalize_station_name` 新設、stg_transactions に正規化駅名 `station_name` 追加、stg_station_master をマクロ化（D-013）
- **検出・修正したバグ**: ①scope_flag の NULL 誤判定（8,226→7,796 に是正・D-014）②stg_land_price の市フィルタ列違い（0件→574地点・D-015）③地価距離の同名駅平均ズレ（中央値328km→242m・D-016）。詳細は errors_and_fixes.md
- 検証結果（Python BigQuery クライアント / scripts/verify_intermediate.py）:
  - stg_transactions: 大阪市24,613行・scope_true **7,796**（D-011一致）・駅名空欄1.91%
  - 駅結合率 **100%**（scope内）・geo NULL 0
  - Fold A train5,725/test2,071=7,796、Fold B train4,142/test1,583
  - 地価: 175駅・距離 min32m/中央値242m/最大5.5km/1000m超4駅・NULL0
  - 新規出現駅でテスト期間の特徴量NULL 9件(0.4%)は既知の限界（D-017）
- **dbt test: PASS=17 / FAIL=0 / ERROR=0**
- 接続: gcloud ハングのため ADCコピー + GOOGLE_CLOUD_PROJECT 指定で実行（errors_and_fixes.md）
- 次にやること: Step 9 mart（mart_condo_price / mart_opportunity_list）。D-017のテスト期間特徴量NULLの扱いを決める

## 2026-06-12 — Step 7: dbt staging 構築（型変換・正規化・スコープ判定）

- 作成モデル: stg_transactions（大阪市24,613行・型変換・D-002/007/008フラグ・scope_flag/excluded_reason）、stg_station_master（D-006正規化）、stg_land_price（公示価格）。BigQuery にview作成・コミット済み（ce88573, 9758c14）
- 注: 当時 scope_flag のNULL扱いと stg_land_price の市フィルタにバグが残存（Step 8 検証で発見し D-014/D-015 で修正）

## 2026-06-12 — Step 6: 分析条件の確定（D-011）

- 10_eda_scope_preview.sql のファネルで件数を確認し、分析スコープを確定: **大阪市・面積20-60㎡・徒歩20分以内・築5-60年・価格500万円以上（上限なし）= 7,796件・駅別10件以上が134駅（生駅名ベース）**。判断根拠は decision_log D-011

## 2026-06-12 — Step 5 改訂: EDA を大阪市スコープで再実行（ユーザー指摘 D-010）

- 指摘: 「分析対象は大阪市なのに府全体で外れ値を見ても閾値の意思決定に使えない」→ 正しいので大阪市版を正式版として全面再実行
- run_eda.py に大阪市フィルターを実装（検査02-09 = 大阪市24,613行。検査10のみ府全体からの絞り込みファネル）
- グラフ9枚・レポートを大阪市版で再生成（タイトルに「大阪市」明記）。キャプション重なりも修正済み
- **府全体と大阪市の差が実証された**: ㎡単価P99は府全体158万 → 大阪市186万円/m2、中央値38.8万 → 50万円/m2。府全体の閾値を使っていたら大阪市の正常な高額物件を外れ値扱いするところだった
- 駅名結合（大阪市）: 208駅名中、正規化後201駅一致・行ベース96.6%。**不一致は7駅名のみ**（四天王寺前夕陽ケ丘287行・ＪＲ難波163・なんば119・あびこ113・鶴ケ丘56・ＪＲ淡路43・ＪＲ野江42）= mapping CSV は7行で済む見込み
- 府全体版の数値は本エントリより下の旧記録に残置（形式チェックの証跡として有効）

## 2026-06-12 — Step 5: EDA 実行（読み取り専用）

- scripts/run_eda.py で一括実行（SQL書き出し→BQ実行→CSV→グラフ→レポートの単一スクリプト = SQLとグラフの連携保証）
- 生成物: sql/checks/02〜10（9本）/ outputs/tables/*.csv（9個）/ outputs/figures/*.png（9枚・結論タイトル+出典キャプション付き）/ docs/eda_report.md（決定事項サマリー+SQL+グラフ+所見+現物5件）
- 主要結果:
  - ㎡単価: 中央値38.8万円/m2、P99=158万円/m2、最大965万円/m2
  - 価格: 中央値2,600万円、P99=1.3億円、最大8.2億円 / 面積: P99=115m2、最大1,960m2
  - 築年数に負値あり（min=-2、建築年>取引年）= D-008 新発見
  - 駅名結合率: 生名一致 362/443駅 → 正規化後 429/443駅、行ベース97.3%。不一致はケ/ヶ・全角ＪＲ・メトロひらがな駅名（D-006）
  - 期間欠落なし、2024年以降件数増
  - 手順書推奨条件適用後: 5,392件・107駅（10件以上）= Step 6 の判断材料
- 判断提案 D-001〜D-008 を decision_log に記録（すべて提案中、Step 6/7 で承認後に確定）
- BigQuery への書き込みなし

## 2026-06-12 — データ辞書作成・BQ列に日本語説明を設定

- `docs/data_dictionary.md` 作成: raw 3種のカラム日本語対応表（国土数値情報の公式属性定義ページ・実データ値と突合して作成。推測なし）
- 重要発見: L01_008=公示価格(円/㎡)、**L01_009=対前年変動率(%)** → land_price_change_rate が年次間結合なしで取得可能
- `scripts/add_column_descriptions.py`: BQ全5テーブルの列スキーマに日本語 description を設定（データ・型・列順は無変更）。raw_transactions 21/21列で反映確認済み

## 2026-06-12 — raw 再ロードと「列と値の対応」検証完了

### 経緯
- データセット `osaka_real_estate` が削除されていることを検知（プロジェクトは健在）→ ユーザー指示により再作成・再ロード
- sql/checks/01_raw_load_validation.sql も消失していたため再作成（未コミットだったため git から復元不可。以後は作成都度コミットを検討）

### 再ロード結果（全9ロード成功・内容無加工）
- raw_transactions 47,386 / raw_station_master_2024 10,235 / _2025 10,234 / raw_land_price_2024 1,715 / _2025 1,687 — すべてソースと一致

### 列と値の対応検証（カラムシフト検出）
- raw_transactions: 13項目のドメイン検査（種類・区分・市区町村コード・都道府県・徒歩分・価格・面積・建築年・構造・取引時期・改装 等）**すべて0件 = 列ズレなし**
- 改装列の実値域は「改装済み」(2,512件) と空欄 (44,874件) のみで「未改装」は存在しない → 空欄は未改装/不明の区別不能（renovation_unknown_flag 設計に反映する）
- GIS: ソースCSVとBQで 行数・路線数(552)・事業者数(176)・駅名数(8,503)・座標合計値が完全一致（station_master_2025）、地価も同様に一致（land_price_2025）
- 教訓: bq へ日本語を含むクエリを stdin で渡すと cp932 誤変換でリテラルが壊れる → **PYTHONUTF8=1 + 引数渡し**で解決（errors_and_fixes 参照）

## 2026-06-12 — Step 3〜4: 投入前確認・BigQuery raw 投入

### Step 3 投入前確認（scripts/precheck_transactions.py）
- ヘッダー: 5年分とも21列で完全一致
- 空文字率: 取引価格・面積・間取り 0% / 最寄駅名 0.3〜2.9% / 徒歩分 6.0〜8.8% / 建築年 0.2〜2.8% / **改装 94.1〜95.8%**（renovation_unknown_flag 設計の妥当性を裏付け）
- 特殊値: 徒歩分に範囲表記47件（「30分～60分」44、「1H30～2H」2、「1H～1H30」1）。面積・建築年・価格の非数値は0件
- 完全重複行: 2021:56 / 2022:46 / 2023:68 / 2024:60 / 2025:100（計330行。staging で重複の扱いを決定する）

### GIS 変換（scripts/gis_to_csv.py）
- ZIP展開: N02-24/25、L01-24/25 → data/gis/raw/ 配下（ZIP原本保持）
- GeoJSON→CSV（属性値は無変更、ジオメトリから lon/lat のみ算出）→ data/gis/processed/
  - station_master_2024.csv: 10,235行（全国） / station_master_2025.csv: 10,234行
  - land_price_2024.csv: 1,715行×146列 / land_price_2025.csv: 1,687行×148列（大阪府）

### BigQuery 投入
- GCPプロジェクト新規作成: `osaka-fudosan-dataanalysis`（課金は旧プロジェクトと同一アカウントに紐付け）
- データセット: `osaka_real_estate`（asia-northeast1）
- ロード（全列STRING・as-is・ヘッダースキップ。成約CSVはcp932→UTF-8変換コピーを使用、rawファイルは無変更）:

| テーブル | 行数 | ソースとの一致 |
|---|---|---|
| raw_transactions（2021〜2025の5ファイル追記） | 47,386 | 一致 |
| raw_station_master_2024 / _2025 | 10,235 / 10,234 | 一致 |
| raw_land_price_2024 / _2025 | 1,715 / 1,687 | 一致 |

### 投入後検証
- 件数: 全テーブルでソースCSVと完全一致
- raw_transactions: 価格 min 100万円〜max 8.2億円（外れ値候補は Step 5 EDA で分類）、面積 15〜1,960㎡、年別の空欄数は投入前確認と整合
- 駅: 駅名空欄0・座標NULL0・経緯度は日本全域の範囲内
- 地価: 座標は大阪府の範囲内（lon 135.1〜135.7 / lat 34.3〜35.0）

### 次にやること
- Step 5: EDA・外れ値確認（sql/checks/ に確認SQLを作成）

## 2026-06-12 — data/samples: 公開用サンプル追加

- `data/samples/osaka_condo_seiyaku_sample.csv`: 2025年成約CSVの先頭10行（UTF-8変換）
- `data/samples/README.md`: 出典・取得条件・21カラムの説明・GISサンプルの追加予定を記載
- 判断: raw全体はコミットしない（成約価格情報の再配布規約が不明確なため）。構造理解用の少量抜粋＋出典明記＋スクリプトによる再現性で代替（decision_log 参照）

## 2026-06-12 — git リポジトリ初期化・初回コミット

- `git init -b main`（ローカルのみ。GitHub への push は Step 13 で実施）
- 取得スクリプト4件を `scripts/` へ移動して追跡対象に追加（extract_pdf.py / download_transactions.py / download_transactions_2025.py / verify_downloads.py）
- 空ディレクトリ14箇所に .gitkeep を追加。data/raw・data/gis/raw は中身を除外しつつ .gitkeep のみ追跡するよう .gitignore を調整
- ステージ内容を検証し、raw データ・認証情報が含まれないことを確認してからコミット
- 注意: scripts/download_transactions*.py に含まれる Ocp-Apim-Subscription-Key は、reinfolib サイトが全ブラウザ訪問者に配布しているフロントエンド公開キーであり、個人の認証情報ではない（GitHub 公開時に README でも明記予定）

## 2026-06-12 — クリーンアップ: 使い捨て調査ファイルの削除

- 削除（データ分析直下）: test_reinfo_api.py / test_reinfo_matrix.py / test_reinfo_browser.py / test_reinfo_browser2.py / test_reinfo_ui.py（reinfolib API調査用ワンショット。成果は download_transactions*.py と errors_and_fixes.md に反映済み）
- 削除（%TEMP%）: JSチャンク・検証レスポンス・スクショ等 26 件
- 保持: extract_pdf.py、manual_v9_extracted.txt、download_transactions.py、download_transactions_2025.py、verify_downloads.py（再取得・再現性の証跡）
- raw データ・旧プロジェクト・docs ログには未接触

## 2026-06-12 — Step 2: データ取得（ダウンロード）

### 実行した内容
- 国土数値情報（nlftp.mlit.go.jp）から直URLでGISデータ4ファイルを `data/gis/raw/` へ取得
- 不動産情報ライブラリ（reinfolib.mlit.go.jp）のWebサイト内部CSVダウンロードAPI（ブラウザのダウンロードボタンと同一の経路・同一の公開キー）で、成約価格CSVを年単位で `data/raw/` へ取得
  - 条件: 大阪府 / 中古マンション等 / 成約価格情報のみ / 各年第1〜第4四半期（旧作業と同一条件）
  - 統合せず年ごとに別ファイルのまま保存
- 取得スクリプト: `scripts/download_transactions.py`、`scripts/download_transactions_2025.py`、検証: `scripts/verify_downloads.py`（2026-06-12 git管理化に伴い scripts/ へ移動）

### 取得結果と検証（件数・内容・整合性）
| ファイル | データ行数 | 検証結果 |
|---|---|---|
| raw/osaka_condo_seiyaku_2020/Osaka Prefecture_20201_20204.csv | 0（ヘッダーのみ） | 成約価格情報の提供が2021年開始のため空。ファイルは証跡として保持 |
| raw/osaka_condo_seiyaku_2021/Osaka Prefecture_20211_20214.csv | 8,505 | 旧ファイルとMD5一致 |
| raw/osaka_condo_seiyaku_2022/Osaka Prefecture_20221_20224.csv | 9,107 | 旧ファイルと行集合完全一致（並び順のみ相違、MD5不一致は順序差） |
| raw/osaka_condo_seiyaku_2023/Osaka Prefecture_20231_20234.csv | 8,975 | 旧ファイルとMD5一致 |
| raw/osaka_condo_seiyaku_2024/Osaka Prefecture_20241_20244.csv | 9,705 | 旧ファイルとMD5一致 |
| raw/osaka_condo_seiyaku_2025/Osaka Prefecture_20251_20254.csv | 11,094 | 新規（2025Q1〜Q4、大容量のためサーバ返却URL経由で取得） |
| gis/raw/N02-24_GML.zip | 22エントリ | ZIP整合性OK・旧ファイルとMD5一致 |
| gis/raw/N02-25_GML.zip | 24エントリ | ZIP整合性OK（新規） |
| gis/raw/L01-24_27_GML.zip | 8エントリ | ZIP整合性OK・旧ファイルとMD5一致 |
| gis/raw/L01-25_27_GML.zip | 8エントリ | ZIP整合性OK（新規） |

- 全CSVで 種類=中古マンション等のみ / 価格情報区分=成約価格情報のみ / 都道府県=大阪府のみ / 四半期4区分そろい を確認
- 2021〜2025 合計データ行数: 47,386行（参考: 大阪市内行 2021:4,124 / 2022:4,529 / 2023:4,724 / 2024:5,200 / 2025:6,036）

### BigQuery で作成・変更したテーブル
- なし（Step 2 はローカル取得のみ）

### 失敗と修正
- reinfolib CSV APIの `kind` パラメータ形式誤りで500エラーが続いた（詳細は errors_and_fixes.md）

### 次にやること
- Step 3: 投入前確認（文字コード・カラム名・行数・NULL候補の確認計画）→ Step 4: BigQuery raw 投入

## 2026-06-12 — Step 1: 接続確認（読み取り専用）

### 確認結果
| ツール | 状態 | 詳細 |
|---|---|---|
| gcloud 認証 | OK | アカウント: ononoomichi@gmail.com (ACTIVE) |
| gcloud プロジェクト | OK | osaka-condo-analysis |
| bq | OK | データセット2件: `osaka_real_estate`, `osaka_real_estate_osaka_real_estate`（後者は旧作業の誤作成分。削除候補だが今回は触らない） |
| dbt | OK | dbt-core 1.11.11 / dbt-bigquery 1.9.0（Python 3.12 の dbt.exe） |
| profiles.yml | 注意 | `~/.dbt/` には無し。旧プロジェクト `osaka-condo-station-opportunity-analysis/dbt/profiles.yml` に存在（dbt実行時はプロジェクト内 dbt/ ディレクトリ参照だった模様） |
| git | OK | 2.54.0.windows.1 |
| gh (GitHub CLI) | 未インストール | GitHub 公開 Step までに導入要否を判断 |
| Tableau | 未確認 | CLI確認不可。接続時に BigQuery コネクタの認証方式と mart 読み取り権限を確認する |

### BigQuery で作成・変更したテーブル
- なし（一覧表示のみ）

### 次にやること
- Step 2: データ配置。旧プロジェクトの data/raw を新プロジェクトへコピーするか、BigQuery 上の既存 raw テーブルを再利用するかを決める

## 2026-06-12 — Step 0: プロジェクト作成

### 実行した内容
- 手順書 `osaka_fudosan_dataanalysis_manual_v9.pdf`（全24ページ）を読み込み（pypdf 6.13.2 をPython 3.12 にインストールしてテキスト抽出 → `../manual_v9_extracted.txt`）
- v9 のディレクトリ構成（PART 2）どおりにフォルダ17個を作成
  - data/{raw, gis/raw, gis/processed, samples}
  - dbt/models/{staging, intermediate, marts}
  - sql/{checks, bqml, ad_hoc}
  - tableau/{data_sources, dashboard_wireframes, screenshots}
  - docs, outputs/{figures, tables, reports}

### 作成したファイル
- CLAUDE.md（PART 3 の作業ルール + v9 特徴量/スコア分離ルール）
- .gitignore（data/raw・data/gis/raw・profiles.yml・認証情報を除外）
- profiles.example.yml（公開用サンプル。実認証情報なし）
- docs/work_log.md・docs/decision_log.md・docs/errors_and_fixes.md（本ファイル群）

### BigQuery で作成・変更したテーブル
- なし（Step 0 は BigQuery 操作なし）

### 確認した件数・NULL率・外れ値
- なし（データ未投入）

### 失敗と修正
- PDF を Read ツールで直接読めず（pdftoppm 不在）→ pypdf によるテキスト抽出で解決（詳細は errors_and_fixes.md）

### 次にやること
- Step 1: BigQuery / dbt / GitHub の接続確認（実行前に確認計画を提示する）
