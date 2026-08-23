# SysstatView フロントエンド (docs/P007-impl-direction/U008-containerization.md)
# ビルドステージ
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# 配信ステージ
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist/sysstatview-frontend/browser /usr/share/nginx/html
EXPOSE 80
