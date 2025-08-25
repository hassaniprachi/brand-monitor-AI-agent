import streamlit as st
import praw
import csv
from textblob import TextBlob
from collections import defaultdict, Counter
import pandas as pd
import os
import matplotlib.pyplot as plt
from datetime import datetime

# ---------- CONFIG ----------
reddit_client_id = "3CvMk9KZtr_76849e4XsaQ"
reddit_client_secret = "LXLTW_go2WyMAzFkE91iknKFtdij4A"
reddit_user_agent = "brand-monitor"

csv_file = "brand_posts_sentiment.csv"

# ---------- DASHBOARD ----------
st.title("Professional Brand Monitoring Dashboard")
brand = st.text_input("Enter Brand Name", "Nike")

# ---------- FETCH POSTS BUTTON ----------
if st.button("Fetch Latest Posts"):
    all_posts = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---------- REDDIT ----------
    try:
        reddit = praw.Reddit(client_id=reddit_client_id,
                             client_secret=reddit_client_secret,
                             user_agent=reddit_user_agent)
        for submission in reddit.subreddit("all").search(brand, limit=5):  # limit to avoid rate limits
            text = submission.title
            sentiment_label = (
                "Positive" if TextBlob(text).sentiment.polarity > 0
                else "Negative" if TextBlob(text).sentiment.polarity < 0
                else "Neutral"
            )
            all_posts.append({
                "platform": "Reddit",
                "text": text,
                "url": submission.url,
                "sentiment": sentiment_label,
                "timestamp": timestamp
            })
    except Exception:
        # fallback silently to CSV if Reddit fails
        if os.path.exists(csv_file):
            reddit_posts = pd.read_csv(csv_file)
            reddit_posts = reddit_posts[
                (reddit_posts['platform'] == 'Reddit') &
                (reddit_posts['text'].str.contains(brand, case=False, na=False))
            ].tail(5).to_dict('records')
            all_posts.extend(reddit_posts)

    # ---------- TWITTER (CSV ONLY) ----------
    if os.path.exists(csv_file):
        df_csv = pd.read_csv(csv_file)
        twitter_posts = df_csv[
            (df_csv['platform'] == 'Twitter') &
            (df_csv['text'].str.contains(brand, case=False, na=False))
        ].tail(5).to_dict('records')
        all_posts.extend(twitter_posts)

    # ---------- SAVE TO CSV ----------
    if all_posts:
        if os.path.exists(csv_file):
            existing_urls = set()
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_urls.add(row["url"])
            new_posts = [p for p in all_posts if p["url"] not in existing_urls]
        else:
            new_posts = all_posts

        if new_posts:
            with open(csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["platform", "text", "url", "sentiment", "timestamp"])
                if os.stat(csv_file).st_size == 0:
                    writer.writeheader()
                writer.writerows(new_posts)
            st.success(f"✅ Added {len(new_posts)} new posts")
        else:
            st.info("No new posts found.")

# ---------- LOAD DATA ----------
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
    df_brand = df[df['text'].str.contains(brand, case=False, na=False)]
    
    if not df_brand.empty:
        st.subheader(f"Total Posts Collected for {brand}: {len(df_brand)}")

        platforms = st.multiselect(
            "Select Platforms",
            options=df_brand['platform'].unique(),
            default=df_brand['platform'].unique()
        )
        sentiments = st.multiselect(
            "Select Sentiments",
            options=["Positive", "Neutral", "Negative"],
            default=["Positive", "Neutral", "Negative"]
        )
        df_filtered = df_brand[(df_brand['platform'].isin(platforms)) & (df_brand['sentiment'].isin(sentiments))]

        st.subheader("Latest Posts")
        st.dataframe(
            df_filtered[['platform', 'text', 'sentiment', 'url', 'timestamp']]
            .sort_values(by='timestamp', ascending=False)
            .head(20)
        )

        # ---------- Platform-wise Sentiment Plot ----------
        platform_sentiment = defaultdict(Counter)
        for _, row in df_filtered.iterrows():
            platform_sentiment[row["platform"]][row["sentiment"]] += 1

        plt.figure(figsize=(8,5))
        x = range(len(platform_sentiment))
        width = 0.2
        platforms_list = list(platform_sentiment.keys())
        values = {s: [platform_sentiment[p][s] for p in platforms_list] for s in ["Positive","Neutral","Negative"]}

        plt.bar([i - width for i in x], values["Positive"], width=width, label="Positive", color="green")
        plt.bar(x, values["Neutral"], width=width, label="Neutral", color="gray")
        plt.bar([i + width for i in x], values["Negative"], width=width, label="Negative", color="red")
        plt.xticks(x, platforms_list)
        plt.ylabel("Number of Posts")
        plt.title(f"Platform-Wise Sentiment for {brand}")
        plt.legend()
        st.pyplot(plt)

        # ---------- Daily Sentiment Trend ----------
        df_filtered['date'] = pd.to_datetime(df_filtered['timestamp']).dt.date
        trend = df_filtered.groupby(['date','sentiment']).size().unstack(fill_value=0)
        st.subheader("Daily Sentiment Trend")
        st.line_chart(trend)
    else:
        st.info("No posts available for this brand yet.")
else:
    st.info("No data available yet. Click 'Fetch Latest Posts' to start.")
