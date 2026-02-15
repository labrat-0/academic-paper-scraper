FROM apify/actor-python:3.12

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["python", "-m", "src"]
