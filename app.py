from contextlib import redirect_stderr, redirect_stdout
from flask import Flask, render_template, request, redirect, url_for, session
import requests
from newspaper import Article
import google.generativeai as genai
import os
import json
import re
import random

app = Flask(__name__)
# セッションを使用するために、秘密鍵を設定する必要があります。
# 本番環境ではより複雑で安全な鍵を使用してください。
app.secret_key = "your_super_secret_key"

API_KEY = "ee4dda9a38ff5a93a69fefc277f06829"

# Gemini API Key
# 環境変数から読み込むことを推奨します
GEMINI_API_KEY = "AIzaSyCJJIyoY__PPJCIVxPsLLp8oGRe0oDeydY"

# Gemini APIの初期化
genai.configure(api_key=GEMINI_API_KEY)

model_name_to_use = "models/gemini-1.5-flash-latest"
model = genai.GenerativeModel(model_name_to_use)


# ニュースの要約をするルート
def summarize_article_with_gemini(text):
    # エラー時のデフォルト値を定義
    default_error_response = "記事の分析に失敗しました。"
    try:
        # プロンプトを出来事の構造分析に特化させる
        # ここをJSONではなく、一つの文章を生成するように変更
        prompt = f"""
以下の記事を分析し、記事の要約、出来事の背景、出来事の構造（いつ、どこで、誰が、何を、なぜ、どうなったか）をすべて含んだ、一つの簡潔な文章で出力してください。
出力はMarkdownのコードブロック記号を含まず、文章のみを生成してください。

記事本文:
{text}
"""
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
            ),
        )

        if response and response.candidates:
            # 取得した文章をそのまま返す
            return response.candidates[0].content.parts[0].text
        else:
            print("Gemini APIからの分析レスポンスが空でした。")
            return default_error_response
    except Exception as e:
        print(f"Gemini APIによる記事分析中にエラーが発生しました: {e}")
        return default_error_response


# ニュース活用の提案をするルート
def suggest_article_with_gemini(text):
    # エラー時のデフォルト値を定義
    default_error_response = "記事の分析に失敗しました。"
    try:
        # プロンプトを出来事の構造分析に特化させる
        # ここをJSONではなく、一つの文章を生成するように変更
        prompt = f"""
以下の記事を分析し、このニュースをどの業界における就職活動のどの場面でどう活用できるのかを具体的に2文で示してください。それぞれの定義は以下の通りです。どの業界：金融、商社、外資、食品、ITなどあらゆる切り口から見た業界、どの場面：面接、ES、OBOG訪問など選考フローにおけるあらゆる場面、どう活用できるか：知識や理解を面接官にアピールするためにニュースを通り活用できるか具体例を示す

記事本文:
{text}
"""
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
            ),
        )

        if response and response.candidates:
            # 取得した文章をそのまま返す
            return response.candidates[0].content.parts[0].text
        else:
            print("Gemini APIからの分析レスポンスが空でした。")
            return default_error_response
    except Exception as e:
        print(f"Gemini APIによる記事分析中にエラーが発生しました: {e}")
        return default_error_response


# ニュース検索フォームを表示するルート
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        keyword = request.form.get("keyword")
        if keyword:
            return redirect(url_for("select", keyword=keyword))

    # HTMLテンプレートをレンダリングし、データを渡す
    return render_template("home.html")

    # return render_template("home.html")


@app.route("/gacha")
def gacha():
    words = [
        "猫",
        "天気",
        "野球",
        "AI",
        "旅行",
        "気候変動",
        "宇宙開発",
        "テクノロジー",
        "医療",
        "料理",
        "歴史",
        "アート",
        "スポーツ",
        "ゲーム",
    ]
    keyword = random.choice(words)
    return redirect(url_for("select", keyword=keyword))


@app.route("/select", methods=["GET", "POST"])
def select():
    if request.method == "POST":
        keyword = request.form.get("keyword")
        if keyword:
            return redirect(url_for("select", keyword=keyword))

    # GETリクエストの場合（URLからの直接アクセスやリダイレクト）
    keyword = request.args.get("keyword")
    if not keyword:
        return redirect(url_for("home"))

    url = f"https://gnews.io/api/v4/search?q={keyword}&lang=ja&max=4&token={API_KEY}"
    response = requests.get(url).json()

    global search_results
    search_results = response.get("articles", [])

    return render_template("select.html", articles=search_results, keyword=keyword)


# -------- 詳細ページ --------
@app.route("/detail/<int:article_id>")
def detail(article_id):
    # セッションから検索結果を取得
    search_results = session.get("search_results")

    # セッションに検索結果がない場合は、ホームページにリダイレクト
    if not search_results or article_id < 0 or article_id >= len(search_results):
        return redirect(url_for("home"))

    article_data = search_results[article_id]
    article_url = article_data["url"]

    # 本文取得
    article = Article(article_url, language="ja")
    article.download()
    article.parse()

    # Gemini分析
    # summaryze_article_with_gemini関数が文字列を返すように変更したため、戻り値も文字列になる
    summary_text = summarize_article_with_gemini(article.text)
    suggestion_text = suggest_article_with_gemini(article.text)

    return render_template(
        "detail.html",
        title=article_data["title"],
        publishedAt=article_data["publishedAt"],
        url=article_url,
        content=article.text,
        # 複数の項目ではなく、1つの文章としてHTMLに渡す
        summary_text=summary_text,
        suggestion_text=suggestion_text,
    )


if __name__ == "__main__":
    app.run(debug=True)
# Herokuへの強制プッシュのための変更（6回目）
