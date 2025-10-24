# st-error-boundary

[English](README.md) | 日本語

Streamlitアプリケーションのための、ミニマルで型安全なエラーバウンダリライブラリです。プラグイン可能なフックと安全なフォールバックUIを提供します。

## 解決したい課題

Streamlitは、デフォルトでは例外発生時に詳細なスタックトレースをブラウザに表示します。これは開発中は便利ですが、本番環境ではセキュリティリスクになりえます。
`client.showErrorDetails = "none"` を設定すれば情報漏洩は防げますが、ユーザーには画一的なエラーメッセージしか表示されず、何が起きているのか分からず困惑させてしまいます。

これまでの一般的な解決策は、コードの様々な場所に`st.error()`と`st.stop()`を配置するものでした。しかし、この方法は**コードの可読性と保守性を著しく低下**させるだけでなく、重要な箇所で**例外処理を実装し忘れる**リスクも生み出します。

このライブラリは、**デコレーターパターン**を用いてこの問題を解決します。例外処理という「横断的関心事」をビジネスロジックから切り離し、アプリケーションのメイン関数に「最後の防衛線」としてデコレーターを1つ追加するだけです。こうすることで全ての未処理例外をキャッチし、ユーザーフレンドリーなメッセージを表示することができるので、エラーハンドリングのための定型コードをあちこちに書く必要はありません。

このパターンは、実際の開発で培われた知見を一部抽出してオープンソース化したものです。
コードの明瞭性を損なうことなく、堅牢なStreamlitアプリケーションを構築する手助けとなることを目指しています。アーキテクチャの全体像については、[PyConJP 2025での発表資料](https://speakerdeck.com/kdash/streamlit-hashe-nei-turudakeziyanai-poc-nosu-sadeshi-xian-surushang-yong-pin-zhi-nofen-xi-saas-akitekutiya)をご覧ください。

特に**顧客向け**のアプリケーションや**規制の厳しい**環境では、内部情報が漏洩する未処理例外は単なる表示上の問題ではなく、**ビジネス上のインシデント**に繋がりかねません。
UIにはスタックトレースを表示せず、しかし裏側の監視システムには**サニタイズ（無害化）された豊富な情報**を送信することが理想的であると考えます。

## 対象となるユーザー

**顧客向けのStreamlitアプリケーション（B2B/B2C、規制産業、エンタープライズ環境など）**を開発・運用するチームを想定しています。
UIには**スタックトレースを表示せず**、`on_error`フックを使って**サニタイズ済みの詳細なエラー情報**を監視基盤に送信することで、**一貫性のあるユーザーフレンドリーなエラー表示**と、**運用に必要な十分なテレメトリ**の両立を実現します。


## 主な機能

- **ミニマルなAPI**
  - 必須の引数は`on_error`と`fallback`の2つだけです。
- **PEP 561準拠**
  - `py.typed`ファイルを同梱しており、型チェッカーによる静的解析を完全にサポートします。
- **コールバックの保護**
  - デコレーターを付与した関数だけでなく、`on_click`や`on_change`といったウィジェットのコールバック関数も保護します。
- **プラグイン可能なフック**
  - エラー発生時に、監査ログの記録、メトリクスの送信、通知など、任意の副作用を実行できます。
- **安全なフォールバックUI**
  - スタックトレースの代わりに、ユーザーフレンドリーなエラーメッセージやコンポーネントを表示します。

## インストール

```bash
pip install st-error-boundary
```

## クイックスタート

### 基本的な使い方（デコレーターのみ）

アプリケーションのメイン関数のみを保護するシンプルなケースです。

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# エラーバウンダリのインスタンスを作成
boundary = ErrorBoundary(
    on_error=lambda exc: print(f"エラー情報を記録しました: {exc}"),
    fallback="エラーが発生しました。時間をおいてから再度お試しください。"
)

@boundary.decorate
def main() -> None:
    st.title("My App")

    if st.button("エラーを発生させる"):
        raise ValueError("何らかのエラーが発生しました")

if __name__ == "__main__":
    main()
```

#### ⚠️ 重要
`@boundary.decorate`デコレーターだけでは、`on_click`や`on_change`で指定されたコールバック関数内で発生した例外を捕捉**できません**。
コールバックを保護するには、後述の「高度な使い方」で説明する`boundary.wrap_callback()`を使用する必要があります。

### 高度な使い方（コールバック関数あり）

メイン関数とウィジェットのコールバック関数の両方を保護する場合です。

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

def audit_log(exc: Exception) -> None:
    # 監視サービスにログを送信するなどの処理
    print(f"監査ログ: {exc}")

def fallback_ui(exc: Exception) -> None:
    st.error("予期しないエラーが発生しました。")
    st.link_button("サポートへのお問い合わせ", "https://example.com/support")
    if st.button("再試行"):
        st.rerun()

# 設定を共通化するため、ErrorBoundaryのインスタンスを1つ作成
boundary = ErrorBoundary(on_error=audit_log, fallback=fallback_ui)

def handle_click() -> None:
    # この関数はエラーを発生させます
    result = 1 / 0

@boundary.decorate
def main() -> None:
    st.title("My App")

    # 保護対象: if文の中で発生するエラー
    if st.button("直接的なエラー"):
        raise ValueError("main関数内でエラーが発生しました")

    # 保護対象: コールバック関数の中で発生するエラー
    st.button(
        "コールバックエラー",
        on_click=boundary.wrap_callback(handle_click)
    )

if __name__ == "__main__":
    main()
```

## 従来パターンとの対比（try/except を書かない）

### 従来: 画面ごとに try/except と `st.error()` / `st.stop()` を散りばめる

```python
from __future__ import annotations
import streamlit as st

def save_profile(name: str) -> None:
    if not name:
        raise ValueError("名前は必須です")
    # …永続化…

def main() -> None:
    st.title("プロフィール")
    name: str = st.text_input("名前", "")
    if st.button("保存"):
        try:
            save_profile(name)
            st.success("保存しました")
        except ValueError as exc:
            st.error(f"入力エラー: {exc}")
            st.stop()  # エラー後のUI崩れを防ぐため停止

if __name__ == "__main__":
    main()
```

* 課題: 例外処理が**重複・散在**し、**書き忘れのリスク**や可読性低下を招く。横断関心事がドメインロジックに漏れ込みがち。

### ErrorBoundary: 呼び出し側は **raise するだけ**（UI表示と副作用は境界に集約）

```python
from __future__ import annotations
import streamlit as st
from st_error_boundary import ErrorBoundary

def audit_log(exc: Exception) -> None:
    # 監査ログやメトリクス送信
    print(f"[audit] {exc!r}")

def fallback_ui(exc: Exception) -> None:
    st.error("予期しないエラーが発生しました。時間をおいて再度お試しください。")
    if st.button("リトライ"):
        st.rerun()

boundary: ErrorBoundary = ErrorBoundary(
    on_error=audit_log,
    fallback=fallback_ui,  # 文字列も可（内部で st.error() により描画）
)

def save_profile(name: str) -> None:
    if not name:
        raise ValueError("名前は必須です")
    # …永続化…

@boundary.decorate
def main() -> None:
    st.title("プロフィール")
    name: str = st.text_input("名前", "")
    if st.button("保存"):
        # ここでは try/except を書かず、ドメイン例外は raise で OK
        save_profile(name)

if __name__ == "__main__":
    main()
```

* **利点**: エラー UI とフックを**一箇所に集約**でき、main 関数内のロジックをクリーンに保てる。`fallback` が文字列なら内部で `st.error()` により描画（自由な UI はコール可能を渡す）
* コールバック（`on_click` / `on_change`）はデコレータの外で実行されるため、**`boundary.wrap_callback(...)` で明示的にラップ**する。
* `st.rerun()` / `st.stop()` のような**制御用の例外は素通し**される。意図した制御では引き続き使用できる（エラー処理のボイラープレートとして `st.stop()` を書く必要はない）

### それでもローカルの try/except を残すべき場面

* **その場で回復**したい（例: 入力補正して処理続行）。
* **特定の例外だけ別 UI** を出したいなど、**細粒度の分岐 UI** が要る。
* 外部 API の**ローカルリトライ**を実装し、例外を握りつぶして再処理する設計上の意図がある。

## ErrorBoundaryクラスが必要な理由

Streamlitは、`on_click`や`on_change`で指定されたコールバック関数をスクリプトが再実行される**前**に実行します。
これは、コールバック関数がデコレーターで修飾された関数のスコープ**外**で実行されることを意味します。これが、`@boundary.decorate`だけではコールバック関数内のエラーを捕捉できない理由です。

**（例）実行フロー**
1. ユーザーが`on_click=callback`が設定されたボタンをクリック
2. Streamlitが`callback()`を実行 → **この時点ではデコレーターの保護下にない**
3. Streamlitがスクリプトを再実行
4. デコレーターで保護された関数が実行される → **このスコープは保護下にある**

### 解決策
`boundary.wrap_callback()`を使い、コールバック関数を明示的に同じエラーハンドリングロジックでラップします。

## APIリファレンス

### `ErrorBoundary`

```python
ErrorBoundary(
    on_error: ErrorHook | Iterable[ErrorHook],
    fallback: str | FallbackRenderer
)
```

#### パラメータ
- `on_error`: エラー発生時の副作用（ロギング、メトリクス送信など）を実行するフック関数、またはそのリスト。
- `fallback`: エラー時に表示するUI。文字列、またはカスタムUIをレンダリングする関数のいずれかを指定します。
  - `fallback`に文字列を指定した場合、内部で`st.error()`を使って表示されます。
  - `st.warning()`や独自のウィジェットなど、表示をカスタマイズしたい場合は、`FallbackRenderer`に準拠した関数を渡してください。

#### メソッド
- `.decorate(func)`: 関数をエラーバウンダリでラップするためのデコレーターです。
- `.wrap_callback(callback)`: `on_click`や`on_change`などのウィジェットコールバック関数をラップします。

### `ErrorHook` プロトコル

```python
def hook(exc: Exception) -> None:
    """副作用を伴う例外処理を実装します。"""
    ...
```

### `FallbackRenderer` プロトコル

```python
def renderer(exc: Exception) -> None:
    """例外発生時の代替UIをレンダリングします。"""
    ...
```

## 使用例

### 複数のフック関数を登録する

```python
import logging

def log_error(exc: Exception) -> None:
    logging.error(f"エラーが発生しました: {exc}")

def send_metric(exc: Exception) -> None:
    metrics.increment("app.errors")

boundary = ErrorBoundary(
    on_error=[log_error, send_metric],  # フックはリストの順に実行されます
    fallback="エラーが発生しました。"
)
```

### フォールバックUIをカスタマイズする

```python
def custom_fallback(exc: Exception) -> None:
    st.error(f"エラー種別: {type(exc).__name__}")
    st.warning("もう一度お試しいただくか、サポートまでお問い合わせください。")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("再試行"):
            st.rerun()
    with col2:
        st.link_button("不具合を報告", "https://example.com/bug-report")

boundary = ErrorBoundary(on_error=lambda _: None, fallback=custom_fallback)
```

## 重要な注意点

### コールバックエラーの表示位置

コールバック内で発生したエラーは、デフォルトではページ最上部に表示されます。エラーの表示位置を制御したい場合は、後述の「遅延レンダリングパターン」を使用してください。

`wrap_callback()`を使用した場合、コールバック関数（`on_click`や`on_change`）内で発生したエラーのフォールバックUIは、エラーを引き起こしたウィジェットの近くではなく、**ページの最上部**に表示されます。これはStreamlitのアーキテクチャ上の制約によるものです。

#### 遅延レンダリングパターン

この問題を回避するには、コールバック実行時にはエラー情報を`session_state`に保存するだけに留め、メインのスクリプトが再実行されるタイミングでその情報をレンダリングします。

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# session_stateの初期化
if "error" not in st.session_state:
    st.session_state.error = None

# エラーをすぐにレンダリングせず、session_stateに保存
boundary = ErrorBoundary(
    on_error=lambda exc: st.session_state.update(error=str(exc)),
    fallback=lambda _: None  # ここでは何も表示せず、メインスクリプトでの描画に任せる
)

def trigger_error():
    raise ValueError("コールバック内でエラーが発生しました！")

# --- メインのアプリケーション ---
st.button("クリック", on_click=boundary.wrap_callback(trigger_error))

# ボタンの下でエラー情報をレンダリング
if st.session_state.error:
    st.error(f"エラー: {st.session_state.error}")
    if st.button("エラーをクリア"):
        st.session_state.error = None
        st.rerun()
```

上記により、エラーメッセージがページ最上部ではなく**ボタンの下**に表示されるようになります。

詳細は[コールバックのレンダリング位置に関するガイド](docs/callback-rendering-position.md)（英語）を参照してください。

### ネストされたErrorBoundaryの挙動

`ErrorBoundary`のインスタンスがネスト（入れ子）になっている場合、以下のルールが適用されます。

1. **最も内側のバウンダリが最初に処理する**
    - 例外を最初に捕捉した、最も内側のバウンダリがエラーを処理します。

2. **内側のフックのみが実行される**
    - 内側のバウンダリが例外を処理した場合、**そのバウンダリに登録されたフックのみが実行されます**。外側のバウンダリのフックは実行されません。

3. **フォールバック処理中の例外は上位に伝播する (バブルアップ)**
    - 内側のバウンダリのフォールバック処理（`fallback`）の実行中に例外が発生した場合、その例外は外側のバウンダリに伝播し、外側が処理します。これは、フォールバック処理自体のバグが握り潰されるのを防ぐための仕様です。

4. **Streamlitの制御フロー例外は常に通過する**
    - `st.rerun()`や`st.stop()`のようなStreamlitの制御フロー例外は、全てのバウンダリで捕捉されず、そのまま通過します。

5. **コールバックも同じルールに従う**
    - `wrap_callback()`でラップされたコールバックも、上記のネストルールに従います。コールバックをラップしている最も内側のバウンダリが例外を処理します。

#### 例: 内側のバウンダリがエラーを処理するケース

```python
outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback="INNER")

@outer.decorate
def main():
    @inner.decorate
    def section():
        raise ValueError("boom")
    section()
```

##### 結果
- `INNER`のフォールバックUIが表示されます。
- `inner_hook`のみが呼び出されます（`outer_hook`は呼び出されません）。

#### （例）フォールバック処理中の例外が上位に伝播するケース

```python
def bad_fallback(exc: Exception):
    raise RuntimeError("フォールバック処理に失敗しました")

outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback=bad_fallback)

@outer.decorate
def main():
    @inner.decorate
    def section():
        raise ValueError("boom")
    section()
```

##### 結果
- 内側のフォールバック処理で例外が発生したため、`OUTER`のフォールバックUIが表示されます。
- `inner_hook`が最初に呼び出され、その後`outer_hook`も呼び出されます。

#### ベストプラクティス

- **内側のフォールバック**: UIをレンダリングして処理を完了させることを推奨します（例外を`raise`しない）。これにより、エラーの影響範囲を局所化できます。
- **外側のフォールバック**: 特定のエラーを意図的に外側のバウンダリで処理させたい場合は、内側のフォールバックから明示的に`raise`してください。

#### テストカバレッジ

ネストされたバウンダリの全ての挙動は、自動テストによって検証されています。
実装の詳細は[`tests/test_integration.py`](tests/test_integration.py)をご覧ください。

## 開発

```bash
# 依存関係のインストール
make install

# pre-commitフックのインストール (推奨)
make install-hooks

# リンターと型チェッカーの実行
make

# テストの実行
make test

# サンプルアプリの実行
make example

# デモの実行
make demo
```

### Pre-commitフック

このプロジェクトでは、コミット前にコード品質チェックを自動的に実行するために[pre-commit](https://pre-commit.com/)を使用しています。

- **コードフォーマット**: ruff format
- **リンター**: ruff check
- **型チェック**: mypy, pyright
- **テスト**: pytest
- **その他**: 末尾の空白、ファイル終端、YAML/TOMLの検証など

以下の手順でセットアップしてください。

```bash
# pre-commitフックをインストール (初回のみ)
make install-hooks
```

インストール後、`git commit`を実行するとフックが自動的に実行されます。手動で実行する場合は以下のコマンドを使用します。

```bash
# 全てのファイルに対して実行
uv run pre-commit run --all-files

# 特定のコミットでフックをスキップ (非推奨)
git commit --no-verify
```

## ライセンス

MIT

## コントリビューション

コントリビューションを歓迎します！Issueの作成やプルリクエストの送信をお待ちしています。
