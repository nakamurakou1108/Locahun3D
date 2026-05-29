# locahun3d-demo (Cloudflare Worker)

Tiny CORS-adding passthrough for the public R2 demo `.rad` file.

## なぜ必要か

ビューワは `Locahun3D_OfflineViewer.html` 単体で完結する設計で、`.rad`
シーンは Spark の HTTP Range リクエストでチャンク単位にストリーミング
されます。デモシーンは Cloudflare R2 の **public `pub-*.r2.dev`
サブドメイン**にホストされていますが、この URL は仕様上 CORS ヘッダを
一切返しません (`OPTIONS` プリフライトが 403、`GET` 応答も
`Access-Control-Allow-Origin` 無し)。結果として `viewer.locahun3d.com`
や `127.0.0.1` 等の別オリジンから読みに行くと、Spark の `fetchRange`
が連続で `TypeError: Failed to fetch` を吐いてシーンが描画されません。

この Worker は public URL に対する**ホワイトリスト付きの薄いプロキシ**
で、応答に `Access-Control-Allow-Origin: *` 等を貼って返すだけです。
Range / If-Range / ETag / 206 Partial Content は全部スルーするので、
LoD チャンクストリーミングが壊れません。

## デプロイ

```bash
cd demo-proxy
npx wrangler login           # 初回のみ
npx wrangler deploy
```

完了すると Worker URL が表示されます (例:
`https://locahun3d-demo.<account>.workers.dev`)。

## ビューワ側の差し替え

`Locahun3D_OfflineViewer.html` 内の `DEMO_SCENE_URL` を Worker の URL に
書き換えます:

```js
const DEMO_SCENE_URL = 'https://locahun3d-demo.<account>.workers.dev/Kousaten_ForDemo_point_cloud.rad';
```

## カスタムドメインを当てる場合 (任意)

Cloudflare ダッシュボード → Workers & Pages → `locahun3d-demo` →
Settings → Triggers → Custom Domain で `demo.locahun3d.com` 等を割り当て。
HTML の `DEMO_SCENE_URL` もそのドメインに合わせて更新。

## 別のシーンを追加するとき

`src/index.js` の `ALLOWED_PATHS` に新しいパス名を足してから再 deploy。
ホワイトリストにしてあるのは「Worker を経由した不特定オブジェクトの
中継」を物理的に不可能にするためです。

## 動作確認

```bash
# CORS プリフライト
curl -I -X OPTIONS https://locahun3d-demo.<account>.workers.dev/Kousaten_ForDemo_point_cloud.rad \
     -H "Origin: https://viewer.locahun3d.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: range"
# → HTTP/2 204 + Access-Control-Allow-Origin: *

# Range
curl -I -H "Range: bytes=0-1023" https://locahun3d-demo.<account>.workers.dev/Kousaten_ForDemo_point_cloud.rad
# → HTTP/2 206 + Content-Range: bytes 0-1023/372895448 + Access-Control-Allow-Origin: *
```

## ライセンス

ビューワ本体と同じ Apache License 2.0。
