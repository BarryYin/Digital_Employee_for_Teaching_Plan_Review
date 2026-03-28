# Routes

These are the routes defined by the current Flask app in this repository.

## Reachability check

```bash
/usr/bin/curl -I -k https://115.190.176.52
/usr/bin/curl -sS -k https://115.190.176.52 | /usr/bin/sed -n '1,40p'
```

Expected healthy root behavior:

- status `200`
- HTML title contains `教案评审智能体`

Current observed server behavior on 2026-03-28:

- status `200` at the TLS/host layer for `/`
- body is nginx `404 Not Found`

## Common path probe

```bash
for path in / /history /review_result/1 /health /.well-known/agent.json; do
  printf 'PATH %s\n' "$path"
  /usr/bin/curl -sS -k -D - "https://115.190.176.52$path" -o /tmp/tpr.out | /usr/bin/sed -n '1,12p'
  /usr/bin/sed -n '1,8p' /tmp/tpr.out
  printf '\n'
done
```

If these all return nginx 404 HTML, the app is not exposed on those paths.

## Remote form submission

Use this only after confirming the app is mounted.

```bash
/usr/bin/curl -sS -k -D /tmp/tpr_headers.txt -o /tmp/tpr_body.txt \
  -X POST "https://115.190.176.52/submit_essay" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "title=《春晓》古诗学习" \
  --data-urlencode "grade=五年级" \
  --data-urlencode "content=教学目标是让学生理解古诗内容，体会春天的意境。教学过程包括导入、朗读、讲解、背诵和练习。"
```

Expected healthy behavior:

- response status `302`
- `Location` header points to `/review_result/<id>`

Then fetch the result page:

```bash
/usr/bin/curl -sS -k "https://115.190.176.52/review_result/27" | /usr/bin/sed -n '1,220p'
```

## History pages

```bash
/usr/bin/curl -sS -k "https://115.190.176.52/history" | /usr/bin/sed -n '1,220p'
/usr/bin/curl -sS -k "https://115.190.176.52/history/detail/27" | /usr/bin/sed -n '1,220p'
```

## Result interpretation

If the result page contains text like:

- `评审服务当前不可用`
- `已为你生成本地兜底评审结果`

then the front-end app is reachable, but the upstream workflow is unavailable or timed out.

If the result page contains structured Markdown-style sections such as:

- `### 教案评审结果汇总`
- score tables
- multi-part suggestions

then the upstream workflow succeeded.
