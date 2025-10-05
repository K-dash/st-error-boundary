# Streamlit 用「最後の砦」エラーバウンダリ — コア API 仕様（ErrorBoundary クラス版）

## 1. 概要

* **目的**：ページ（または区画）関数の未捕捉例外を**一箇所で握り**、UI には**安全なフォールバック表示**のみを出す。詳細情報（スタックなど）は**利用者任意のフック**で外部に送る（監査ログ／通知／メトリクス等）。
* **思想**：

  * **何を"する"**（副作用）＝ `on_error`
  * **何を"見せる"**（UI）＝ `fallback`
    この2点のみを**必須**にし、APIを最小化。
* **コールバック対応**：Streamlit の `on_click` / `on_change` コールバックもエラーバウンダリで保護可能。
* **前提**：`client.showErrorDetails="none"` 等のグローバル表示ポリシーと**併存**可能（境界が貼られた範囲では `fallback` を優先）。

---

## 2. 対象・動作モデル

* **対象**：Streamlit アプリのページ関数／セクション関数（重い処理を切り出した小関数にも推奨）
* **動作**：

  1. 対象関数を実行
  2. `Exception` が飛べば **(a)** `on_error` を順に実行 → **(b)** `fallback` を描画
  3. 戻り値は `None`（以降の処理は継続しない想定）
  4. `Exception` のみ捕捉し、それ以外の `BaseException`（例: `KeyboardInterrupt` / `SystemExit` / `GeneratorExit`）は**素通し**

---

## 3. サポート範囲

* **Python**：3.12 以降（PEP 695 のジェネリクス構文を採用）
* **型チェック**：mypy / pyright を通ること
* **依存**：`streamlit>=1.30`（想定）

---

## 4. 公開 API

### 4.1 型（Protocol）

```python
from __future__ import annotations

from typing import Protocol

class ErrorHook(Protocol):
    """例外発生時に任意の副作用を実行（監査ログ・通知・メトリクス等）"""
    def __call__(self, exc: Exception, /) -> None: ...

class FallbackRenderer(Protocol):
    """UI に安全なフォールバック表示を描画（自由なレイアウト可）"""
    def __call__(self, exc: Exception, /) -> None: ...
```

### 4.2 ErrorBoundary クラス

```python
from __future__ import annotations

from collections.abc import Callable, Iterable

class ErrorBoundary:
    """エラーバウンダリの中心クラス。

    on_error と fallback を一箇所で定義し、
    デコレータとコールバックラッパーの両方で使用可能。
    """

    def __init__(
        self,
        on_error: ErrorHook | Iterable[ErrorHook],
        fallback: str | FallbackRenderer,
    ) -> None:
        ...

    def decorate[**P, R](
        self, func: Callable[P, R]
    ) -> Callable[P, R | None]:
        """関数をエラーバウンダリでラップ"""
        ...

    def wrap_callback[**P, R](
        self, callback: Callable[P, R]
    ) -> Callable[P, R | None]:
        """ウィジェットコールバック（on_click等）をラップ"""
        ...
```

* **必須引数**：

  * `on_error`：単体または複数フック。**副作用**（監査・通知・計測など）を好きに差し込む。
  * `fallback`：文字列（同梱プラグインが `st.error("<固定文言>")` を実行）**または**関数（**自由UI**）。
* **メソッド**：
  * `.decorate(func)`：関数デコレータとして使用
  * `.wrap_callback(callback)`：on_click / on_change コールバックをラップ

---

## 5. 仕様詳細

### 5.1 例外の扱い

* `except Exception as exc:` を**最後の砦**として捕捉（制御フロー系など `Exception` 以外の `BaseException` は通す）。
* バウンダリ内で発生した `on_error` の例外は**握りつぶす**（最後の砦が落ちないように）。

### 5.2 フック実行順序

1. `on_error` を**列挙順**で実行（副作用の因果が分かりやすいよう順序は保持）。
2. 各フックの例外は握りつぶし、後続フックの実行を継続。

### 5.3 フォールバック描画の優先規則

* バウンダリの**スコープ内**では、`fallback` が**フレームワーク既定の汎用エラーUIより優先**。
* バウンダリが**無い**箇所では、`client.showErrorDetails` 等のグローバル設定に従う。

### 5.4 スレッド・再実行

* Streamlit の**再実行モデル**に従う。`fallback` 内で `st.rerun()` を呼べば**復旧導線**を提供可能。

---

## 6. 参照実装（最小・完全版）

```python
# pyright: strict
from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import wraps
from typing import ParamSpec, Protocol, TypeVar

from .plugins import render_string_fallback

P = ParamSpec("P")
R = TypeVar("R")

class ErrorHook(Protocol):
    def __call__(self, exc: Exception, /) -> None: ...

class FallbackRenderer(Protocol):
    def __call__(self, exc: Exception, /) -> None: ...

def error_boundary[P, R](
    on_error: ErrorHook | Iterable[ErrorHook],
    fallback: str | FallbackRenderer,
) -> Callable[[Callable[P, R]], Callable[P, R | None]]:
    """未捕捉例外を握り、UIに安全なフォールバックを出す最小デコレータ。

    - on_error: 任意の副作用（監査・通知・計測など）。単体または反復可能。
    - fallback: 固定文言（st.error で表示）または任意UI関数。
    """
    hooks: list[ErrorHook] = (
        list(on_error)
        if isinstance(on_error, Iterable) and not isinstance(on_error, (str, bytes))
        else [on_error]
    )

    def _render_fallback(exc: Exception) -> None:
        if callable(fallback):
            fallback(exc)
        else:
            st.error(fallback)

    def _decorator(func: Callable[P, R]) -> Callable[P, R | None]:
        @wraps(func)
        def _wrapped(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                return func(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:  # noqa: BLE001
                for h in hooks:
                    try:
                        h(exc)
                    except Exception:
                        # フックの失敗で最後の砦を落とさない
                        pass
                _render_fallback(exc)
                return None
        return _wrapped
    return _decorator
```

---

## 7. 使い方（実例）

### 7.1 基本的な使い方

```python
import streamlit as st
from st_error_boundary import ErrorBoundary

# ErrorBoundary インスタンスを作成
boundary = ErrorBoundary(
    on_error=lambda e: print({"event": "unhandled", "error": str(e)}),
    fallback="問題が発生しました。時間をおいて再度お試しください。",
)

@boundary.decorate
def main() -> None:
    st.title("My App")

    # デコレータで保護されたエラー
    if st.button("Trigger Error"):
        raise ValueError("Something went wrong")
```

### 7.2 コールバックも保護（on_click / on_change）

```python
import streamlit as st
from st_error_boundary import ErrorBoundary
from datetime import datetime

def audit(exc: Exception, /) -> None:
    print({"at": datetime.now().isoformat(), "event": "unhandled", "error": str(exc)})

def notify(exc: Exception, /) -> None:
    # 例: Webhook/Slack 通知など
    ...

def fallback_ui(_: Exception, /) -> None:
    st.error("予期しないエラーが発生しました。")
    st.link_button("お問い合わせ", "https://example.com/support")
    if st.button("再試行"):
        st.rerun()

# 単一の ErrorBoundary インスタンスで設定を一元管理
boundary = ErrorBoundary(on_error=[audit, notify], fallback=fallback_ui)

def handle_click() -> None:
    # コールバック内のエラー
    result = 1 / 0

@boundary.decorate
def main() -> None:
    st.title("My App")

    # if 文内のエラー（デコレータで保護）
    if st.button("Direct Error"):
        raise ValueError("Error in main")

    # on_click コールバックのエラー（wrap_callback で保護）
    st.button("Callback Error", on_click=boundary.wrap_callback(handle_click))
```

---

## 8. 非目標（このコアAPIでは扱わない）

* **開発/本番切替（再送出）**：利用者側の流儀に委ねる（必要なら別デコレータで合成）。
* **例外種別ごとの分岐**：`on_error` / `fallback` 内で自由に条件分岐すれば十分。
* **warnings の制御**：別ユーティリティで任意に設定（本コアからは外す）。

---

## 9. 相互運用ポリシー

* `client.showErrorDetails="none"` 等の**グローバル設定**と**併用**することで、境界外の情報漏えいも抑制可能。
* バウンダリの**ネスト**は可能（関数を分割し、局所的に貼ると UX が良い）。

---

## 10. テスト観点（抜粋）

* `Exception` で `on_error` が**全て**呼ばれる／`fallback` が描画される
* `KeyboardInterrupt` / `SystemExit` は**素通し**
* `on_error` 内で例外が起きても**全体が落ちない**
* `fallback` が文字列／関数の**両方**で期待通り表示される
* ネスト（親・子 boundary）で**子が優先**して描画されること

---

## 11. ディレクトリ構成

```
st-error-boundary/
├─ src/
│  └─ st_error_boundary/
│     ├─ __init__.py
│     ├─ error_boundary.py
│     └─ plugins/
│        └─ __init__.py
├─ examples/
│  └─ minimal_app.py
├─ tests/
│  └─ test_error_boundary.py
├─ pyproject.toml
├─ Makefile
├─ README.md
├─ LICENSE
├─ .gitignore
└─ requirements.md        # (本ファイル)
```

* **`src/` レイアウト**：import の健全性が上がり、テストが偶然ローカルソースを拾う事故を防ぐ
* **examples/**：Streamlit 最小デモを置いて **"30秒で動く"** を担保
* **tests/**：例外伝播/握りつぶしの単体テスト
* **Makefile**：開発タスクを統一（fmt/lint/type/test/check）

---

## 12. 開発環境・ツール

* **パッケージ管理**：uv
* **Python**：3.12以降
* **静的解析**：
  * ruff（linter + formatter、ALL ルール適用）
  * pyright（strict モード）
  * mypy（strict モード）
* **テスト**：pytest

### Makefile タスク

```bash
make           # デフォルト: fmt + lint + type
make install   # 依存関係インストール
make fmt       # コードフォーマット
make fmt-check # フォーマットチェック（CI用）
make lint      # リント実行
make type      # 型チェック（pyright + mypy）
make test      # テスト実行
make check     # lint + type + test を一括実行
make example   # デモアプリ起動
make clean     # ビルド成果物削除
```

---

以上が、**必須2引数のみ**を核にした最小コア API の仕様です。
この形なら、利用者は **「何をする / 何を見せる」**だけを決めればよく、実運用の流儀（dev挙動や例外分類）は外側で自由に合成できます。
