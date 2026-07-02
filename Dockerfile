# 1. 軽量なPython公式イメージをベースにする
FROM python:3.11-slim

# 2. コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 3. 必要なシステムパッケージのインストール（Git連携用など）
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. 依存ライブラリを直接インストール
RUN pip install --no-cache-dir \
    streamlit==1.58.0 \
    plotly==6.8.0 \
    pandas==3.0.3 \
    requests==2.31.0 \
    python-dotenv==1.0.1 \
    streamlit-autorefresh==1.0.1

# 5. ソースコードや設定ファイルをコンテナ内にコピー
COPY dashboard.py /app/
COPY .env /app/

# 6. Streamlit用のポートを開放
EXPOSE 8501

# 7. コンテナ起動時にダッシュボードを実行
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]