FROM node:24.22.3-alpine AS build

WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
RUN npm run build

# O build não leva endereço nenhum: o nginx monta /configuracao.json a partir do ambiente
# ao subir o contêiner (nginx/default.conf.template).
FROM nginx:1.30.7-alpine

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
