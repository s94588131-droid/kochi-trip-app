# Jetstar NRT-KCZ 旅行費用チェックアプリ

成田空港から高知空港へJetstarで来る友人向けに、往復航空券、手荷物・座席オプション、ベストプライスホテル高知の宿泊料金、合計金額をローカルで確認するStreamlitアプリです。

まずはモックデータで動きます。外部API接続は `services/flight_api.py` と `services/hotel_api.py` のアダプタを差し替える設計です。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## 主な機能

- 検索条件入力: 出発日、帰宅日、宿泊人数、手荷物プラン、座席指定
- 価格結果: 往路、復路、手荷物、座席、ホテル、合計、前回差額、過去最安比較
- 履歴: SQLiteに保存した価格チェック履歴
- 最安ランキング: 合計金額の安い順
- 設定: 通知しきい値と通知方法
- 通知: Discord WebhookまたはSMTPメール
- 手動入力モード: APIが使えない場合の価格登録
- 半自動モードの構造: Playwrightで公式検索ページの入力補助を将来追加できる設計

## データ保存

SQLiteを使います。初期設定では `travel_prices.sqlite3` に保存します。

`.env` の `DATABASE_PATH` で変更できます。

## API差し替えポイント

### 航空券

`services/flight_api.py` の `FlightApiClient._duffel_search_placeholder()` にDuffel APIなどの実装を追加してください。

想定条件:

- 往路: NRT → KCZ
- 復路: KCZ → NRT
- 航空会社: Jetstar
- 人数: 大人1名

### ホテル

`services/hotel_api.py` の `HotelApiClient._provider_search_placeholder()` に楽天トラベルAPI、Booking.com Demand APIなどの実装を追加してください。

対象ホテル:

- ベストプライスホテル高知

## 注意

このアプリの表示価格は参考価格です。予約前に必ずJetstar公式サイトおよびホテル予約サイトで最終確認してください。

規約違反になる無断スクレイピングは実装していません。Playwrightを使う場合も、個人利用の検索入力補助として公式サイトを開く半自動モードに留める想定です。
