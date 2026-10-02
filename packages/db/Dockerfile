# Migrations as a Cloud Run Job (staging/prod). Locally docker-compose mounts the folder instead.
FROM amacneil/dbmate:2.36.0
COPY migrations /db/migrations
ENV DBMATE_MIGRATIONS_DIR=/db/migrations DBMATE_NO_DUMP_SCHEMA=true
CMD ["--wait", "up"]
