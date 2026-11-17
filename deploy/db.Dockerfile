ARG POSTGRES_IMAGE=postgres:18.7-alpine
FROM ${POSTGRES_IMAGE}
COPY deploy/init-db.sh /docker-entrypoint-initdb.d/10-role.sh
