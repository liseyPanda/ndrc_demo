FROM python:3.12

# working dir
WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy flask app and expose port
COPY . .
EXPOSE 5000

##COPY app.py /app
CMD ["python", "app.py"]

