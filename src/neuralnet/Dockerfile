FROM python:3.10.5-slim

# Create environment variables
ENV DOCKER_MODE="true"

# Set current working directory
WORKDIR /app

# Copy dependency list and install the packages
COPY ./api/requirements.txt ./
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

# Bundle source files
COPY ./api.py ./

# Create data mountpoint
RUN mkdir /data

# Run the app
#CMD ["python", "api.py"]
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "80"]
