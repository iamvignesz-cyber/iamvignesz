FROM node:20-slim

WORKDIR /app
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 3000
CMD ["npm", "start"]
