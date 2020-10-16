FROM node:lts-alpine

# install simple server for static content, not for production!
RUN npm install -g http-server

# Set 'app' folder as current working directory
WORKDIR /app

# Copy package requirement files
COPY package*.json ./

# install project dependencies
RUN npm install

# copy project files and folders
COPY . .

# Build the app
RUN npm run build 

EXPOSE 8080
CMD ["http-server", "dist"]