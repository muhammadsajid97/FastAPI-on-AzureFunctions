# Use the Python 3.9 image
FROM python:3.9-slim-buster

# Copy the Pipfile and Pipfile.lock into the container
COPY Pipfile* /app/

# Set the working directory to /app
WORKDIR /app

# Install pipenv and the Python dependencies
RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

# Install the Azure Functions Core Tools
RUN apt-get update \
    && apt-get install -y wget \
    && wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y azure-functions-core-tools-3

# Set the environment variables
ENV AzureWebJobsScriptRoot=/app \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    PYTHONPATH=/app/WrapperFunction \
    FUNCTIONS_WORKER_RUNTIME=python \
    FUNCTIONS_EXTENSION_VERSION=~3

# Expose port 80
EXPOSE 80

# Start the function app
CMD ["func", "host", "start", "--port", "80"]
