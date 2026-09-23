FROM node:24-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe

ENV NPM_CONFIG_UPDATE_NOTIFIER=false

RUN npm install --global npm@12.0.2

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY frontend/package.json ./frontend/package.json
COPY experiments/package.json ./experiments/package.json
RUN npm ci --workspace frontend --include-workspace-root=false \
    && sha256sum package-lock.json > ./frontend/node_modules/.package-lock.sha256 \
    && mkdir -p /opt/frontend-node-modules \
    && cp -a ./frontend/node_modules/. /opt/frontend-node-modules/ \
    && chown -R node:node /workspace /opt/frontend-node-modules

COPY --chown=node:node frontend ./frontend
COPY frontend/docker-entrypoint.sh /usr/local/bin/fplpatternrec-frontend-entrypoint
RUN chmod +x /usr/local/bin/fplpatternrec-frontend-entrypoint

USER node

ENTRYPOINT ["fplpatternrec-frontend-entrypoint"]
CMD ["npm", "--workspace", "frontend", "run", "dev", "--", "--host", "0.0.0.0"]
