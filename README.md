# grainlog

Logseq風のCLIナレッジ管理ツール。アウトライナー、双方向リンク、デイリーノート、全文検索をターミナルから利用できます。

## インストール

```bash
uvx --from git+https://github.com/yonesuke/grainlog.git grainlog
```

または `uv tool` でグローバルインストール:

```bash
uv tool install git+https://github.com/yonesuke/grainlog.git
grainlog today
```

## 使い方

### デイリーノート

```bash
grainlog today                  # 今日のジャーナルを表示/作成
grainlog daily 2026-02-17       # 指定日のジャーナル
grainlog daily --list           # ジャーナル一覧
```

### ページ・ブロック操作

```bash
grainlog new "プロジェクトA"      # 新規ページ作成
grainlog add "プロジェクトA" "タスク1 [[設計]]"  # ブロック追加（リンク自動検出）
grainlog edit "プロジェクトA"     # $EDITORで編集
grainlog pages                  # ページ一覧
```

### 検索・リンク

```bash
grainlog search "設計"           # 全文検索（FTS5）
grainlog links "設計"            # バックリンク/フォワードリンク表示
```

### タグ

ブロック内の `#tag` を自動検出・インデックスします。

```bash
grainlog add "メモ" "SQLiteの最適化 #performance #db"
grainlog tag list                # 全タグ一覧（使用回数付き）
grainlog tag show performance    # タグ付きブロック一覧
```

### TODO管理

ブロックの先頭に `TODO` / `DONE` を付けて管理します。

```bash
grainlog add "仕事" "TODO 資料を作る"
grainlog add "仕事" "TODO レビュー依頼"
grainlog todo list               # 未完了TODO一覧
grainlog todo list --all         # TODO+DONE 全表示
grainlog todo list --done        # DONE のみ
grainlog todo list --page "仕事" # ページ指定フィルタ
grainlog todo toggle <ID>        # TODO ↔ DONE 切り替え
grainlog todo done <ID> <ID>...  # 複数を一括DONE
grainlog todo clear              # 完了済みを一括削除（確認あり）
grainlog todo clear --force      # 確認なしで一括削除
```

### テンプレート

デイリーノート作成時に雛形が自動挿入されます。

```bash
grainlog template show           # 現在のテンプレート表示
grainlog template edit           # $EDITORで編集
grainlog template path           # テンプレートファイルのパス
```

デフォルトテンプレート:
```
TODO
読んだもの
メモ
```

### エクスポート

```bash
grainlog export --output ./export
```

Logseq互換のMarkdown形式で出力されます:

- ジャーナル → `journals/YYYY_MM_DD.md`
- 通常ページ → `pages/<title>.md`
- `- ` で全行開始、2スペースインデント

### TUI（対話的UI）

```bash
grainlog          # 引数なしでTUI起動
grainlog tui      # 明示的にTUI起動
```

キーバインド: `d` デイリー / `p` ページ一覧 / `s` 検索 / `q` 終了

### 設定確認

```bash
grainlog config   # DBパス等を表示
```

## データ保存先

SQLiteデータベースがOSのデータディレクトリに保存されます:

- **Windows**: `%LOCALAPPDATA%\grainlog\grainlog\grainlog.db`
- **macOS**: `~/Library/Application Support/grainlog/grainlog.db`
- **Linux**: `~/.local/share/grainlog/grainlog.db`

## 開発

```bash
git clone https://github.com/yonesuke/grainlog.git
cd grainlog
uv sync
uv run pytest
```

## ライセンス

MIT
