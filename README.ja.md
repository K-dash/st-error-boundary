# st-error-boundary

[English](README.md) | 日本語

Streamlit アプリケーション向けの、最小限でタイプセーフなエラーバウンダリライブラリ。プラガブルなフックと安全なフォールバック UI を提供します。

## モチベーション

Streamlit のデフォルト動作では、例外が発生するとブラウザに詳細なスタックトレースが表示されます。`client.showErrorDetails = "none"` で情報漏洩は防げますが、一般的なエラーメッセージしか表示されず、ユーザーを混乱させます。典型的な解決策は、コード全体に `st.error()` と `st.stop()` を散りばめることですが、これは**可読性と保守性を著しく低下**させ、重要な箇所で**例外処理を忘れる**リスクを生み出します。

このライブラリは **デコレーターパターン** でこの問題を解決します。単一の「最後の防衛線」デコレーターで、例外処理（横断的関心事）をビジネスロジックから分離します。main 関数をデコレートするだけで、すべての未処理例外がキャッチされ、ユーザーフレンドリーなメッセージが表示されます。エラー処理のボイラープレートでコードを汚す必要はありません。

このパターンは本番環境での使用から一部分を抽出し、オープンソース化したものです。堅牢な Streamlit アプリケーションをコードの明瞭性を犠牲にすることなく構築するためのものです。アーキテクチャの詳細については、[PyConJP 2025 プレゼンテーション](https://speakerdeck.com/kdash/streamlit-hashe-nei-turudakeziyanai-poc-nosu-sadeshi-xian-surushang-yong-pin-zhi-nofen-xi-saas-akitekutiya)を参照してください。

**社外の顧客向け**や**規制業種**の文脈では、内部情報を漏らす未処理例外は単なるノイズではなく、**インシデント**になり得ます。UI にはスタックトレースを出さず、裏側のログ/監視には**マスキング済みの豊富なテレメトリ**を残すことが重要です。

## 本ライブラリの想定利用者

**社外の顧客向けに Streamlit アプリを提供**するチーム（B2B/B2C、規制/エンタープライズ環境）を想定しています。
UI には**スタックトレースを出さず**、`on_error` で**マスキング済みの詳細**を監視基盤へ送ることで、**一貫したユーザー向けエラーメッセージ**と**十分な運用テレメトリ**を両立します。


## 機能

- **最小限の API**: 必須引数は 2 つだけ（`on_error` と `fallback`）
- **PEP 561 準拠**: `py.typed` を同梱し、型チェッカーを完全サポート
- **コールバック保護**: デコレートされた関数とウィジェットコールバック（`on_click`、`on_change` など）の両方を保護
- **任意のフック**: エラー発生時に副作用（監査ログ、メトリクス、通知）を実行
- **安全なフォールバック UI**: トレースバックの代わりにユーザーフレンドリーなエラーメッセージを表示

## インストール

```bash
pip install st-error-boundary
```

## クイックスタート

### 基本的な使い方（デコレーターのみ）

シンプルなケースで、main 関数のみを保護する場合：

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# エラーバウンダリを作成
boundary = ErrorBoundary(
    on_error=lambda exc: print(f"Error logged: {exc}"),
    fallback="エラーが発生しました。後でもう一度お試しください。"
)

@boundary.decorate
def main() -> None:
    st.title("My App")

    if st.button("エラーを発生させる"):
        raise ValueError("何かがうまくいきませんでした")

if __name__ == "__main__":
    main()
```

**⚠️ 重要**: `@boundary.decorate` デコレーターだけでは `on_click`/`on_change` コールバックは**保護されません**。コールバックには `boundary.wrap_callback()` を使用する必要があります（以下の高度な使い方を参照）。

### 高度な使い方（コールバック付き）

デコレートされた関数**と**ウィジェットコールバックの両方を保護する場合：

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

def audit_log(exc: Exception) -> None:
    # 監視サービスにログを送信
    print(f"Error: {exc}")

def fallback_ui(exc: Exception) -> None:
    st.error("予期しないエラーが発生しました。")
    st.link_button("サポートに連絡", "https://example.com/support")
    if st.button("再試行"):
        st.rerun()

# DRY な設定のため、単一の ErrorBoundary インスタンスを使用
boundary = ErrorBoundary(on_error=audit_log, fallback=fallback_ui)

def handle_click() -> None:
    # これはエラーを発生させます
    result = 1 / 0

@boundary.decorate
def main() -> None:
    st.title("My App")

    # 保護されている: if 文内のエラー
    if st.button("直接エラー"):
        raise ValueError("main 関数内のエラー")

    # 保護されている: コールバック内のエラー
    st.button("コールバックエラー", on_click=boundary.wrap_callback(handle_click))

if __name__ == "__main__":
    main()
```

## なぜ ErrorBoundary クラスを使うのか？

Streamlit は `on_click` や `on_change` コールバックをスクリプトが再実行される**前に**実行します。つまり、デコレートされた関数のスコープ**外**で実行されるということです。これが、`@boundary.decorate` だけではコールバックエラーをキャッチできない理由です。

**実行フロー:**
1. ユーザーが `on_click=callback` のボタンをクリック
2. Streamlit が `callback()` を実行 → **デコレーターで保護されていない**
3. Streamlit がスクリプトを再実行
4. デコレートされた関数が実行 → **デコレーターで保護されている**

**解決策**: `boundary.wrap_callback()` を使用して、コールバックを同じエラー処理ロジックで明示的にラップします。

## API リファレンス

### `ErrorBoundary`

```python
ErrorBoundary(
    on_error: ErrorHook | Iterable[ErrorHook],
    fallback: str | FallbackRenderer
)
```

**パラメータ:**
- `on_error`: 副作用（ログ、メトリクスなど）のための単一のフックまたはフックのリスト
- `fallback`: 文字列（`st.error()` で表示）またはカスタム UI をレンダリングする callable
  - `fallback` が `str` の場合、内部で `st.error()` を使用してレンダリングされます
  - レンダリングをカスタマイズする場合（例: `st.warning()` やカスタムウィジェットを使用）、代わりに `FallbackRenderer` callable を渡してください

**メソッド:**
- `.decorate(func)`: 関数をエラーバウンダリでラップするデコレーター
- `.wrap_callback(callback)`: ウィジェットコールバック（on_click、on_change など）をラップ

### `ErrorHook` プロトコル

```python
def hook(exc: Exception) -> None:
    """副作用で例外を処理します。"""
    ...
```

### `FallbackRenderer` プロトコル

```python
def renderer(exc: Exception) -> None:
    """例外のフォールバック UI をレンダリングします。"""
    ...
```

## サンプル

### 複数のフック

```python
def log_error(exc: Exception) -> None:
    logging.error(f"Error: {exc}")

def send_metric(exc: Exception) -> None:
    metrics.increment("app.errors")

boundary = ErrorBoundary(
    on_error=[log_error, send_metric],  # フックは順番に実行されます
    fallback="エラーが発生しました。"
)
```

### カスタムフォールバック UI

```python
def custom_fallback(exc: Exception) -> None:
    st.error(f"エラー: {type(exc).__name__}")
    st.warning("もう一度試すか、サポートに連絡してください。")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("再試行"):
            st.rerun()
    with col2:
        st.link_button("バグを報告", "https://example.com/bug-report")

boundary = ErrorBoundary(on_error=lambda _: None, fallback=custom_fallback)
```

## 重要な注意事項

### コールバックエラーのレンダリング位置

**TL;DR**: コールバック内のエラーはウィジェットの近くではなく、ページの上部に表示されます。エラー位置を制御するには、遅延レンダリングパターン（以下）を使用してください。

`wrap_callback()` を使用すると、ウィジェットコールバック（`on_click`、`on_change`）内のエラーは、ウィジェットの近くではなく**ページの上部**にレンダリングされます。これは Streamlit のアーキテクチャ上の制限です。

#### 遅延レンダリングパターン

コールバック実行中にエラーを `session_state` に保存し、メインスクリプト実行中にレンダリングします：

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# session_state を初期化
if "error" not in st.session_state:
    st.session_state.error = None

# レンダリングする代わりにエラーを保存
boundary = ErrorBoundary(
    on_error=lambda exc: st.session_state.update(error=str(exc)),
    fallback=lambda _: None  # サイレント - メインスクリプトに任せる
)

def trigger_error():
    raise ValueError("コールバック内のエラー!")

# メインアプリ
st.button("クリック", on_click=boundary.wrap_callback(trigger_error))

# ボタンの後にエラーをレンダリング
if st.session_state.error:
    st.error(f"エラー: {st.session_state.error}")
    if st.button("クリア"):
        st.session_state.error = None
        st.rerun()
```

**結果**: エラーが上部ではなく**ボタンの下**に表示されます。

詳細については、[コールバックレンダリング位置ガイド](docs/callback-rendering-position.md)を参照してください。

### ネストされた ErrorBoundary の動作

`ErrorBoundary` インスタンスがネストされている（階層的な）場合、以下のルールが適用されます：

1. **内側の boundary が最初に処理**（ファーストマッチの原則）
    - 例外をキャッチした最も内側の boundary が処理します。

2. **内側のフックのみ実行**
    - 内側の boundary が例外を処理する場合、**内側の boundary のフックのみが呼ばれます**。外側の boundary のフックは実行されません。

3. **fallback の例外はバブルアップ**
    - 内側の boundary の fallback が例外を raise した場合、その例外は外側の boundary に伝播します。外側の boundary がそれを処理します（設計上、fallback のバグは静かに無視されません）。

4. **制御フロー例外は素通り**
    - Streamlit の制御フロー例外（`st.rerun()`、`st.stop()`）は、**すべて**の boundary を通過してキャッチされません。

5. **コールバックにも同じルール**
    - `wrap_callback()` も同じネストルールに従います。コールバックをラップしている最も内側の boundary が例外を処理します。

#### 例: 内側の Boundary が処理

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

**結果**:
- `INNER` fallback が表示されます
- `inner_hook` のみが呼ばれます（`outer_hook` は呼ばれません）

#### 例: Fallback の例外がバブルアップ

```python
def bad_fallback(exc: Exception):
    raise RuntimeError("fallback failed")

outer = ErrorBoundary(on_error=outer_hook, fallback="OUTER")
inner = ErrorBoundary(on_error=inner_hook, fallback=bad_fallback)

@outer.decorate
def main():
    @inner.decorate
    def section():
        raise ValueError("boom")
    section()
```

**結果**:
- `OUTER` fallback が表示されます（内側の fallback が例外を raise）
- `inner_hook` と `outer_hook` の両方が呼ばれます（inner が先、次に outer）

#### ベストプラクティス

- **内側の fallback**: UI をレンダリングして終了する（raise しない）。これによりエラーが分離されます。
- **外側の fallback**: 特定のエラーを外側の boundary に処理させたい場合は、内側の fallback から明示的に `raise` してください。

#### テストカバレッジ

すべてのネストされた boundary の動作は自動テストで検証されています。
実装の詳細については、[`tests/test_integration.py`](tests/test_integration.py) を参照してください。

## 開発

```bash
# 依存関係のインストール
make install

# リントと型チェックの実行
make

# テストの実行
make test

# サンプルアプリの実行
make example
```

## ライセンス

MIT

## コントリビューション

コントリビューションを歓迎します！Issue を開くか、プルリクエストを送信してください。
