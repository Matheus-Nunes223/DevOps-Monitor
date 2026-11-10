FROM busybox:1.36.1 AS healthcheck
FROM coredns/coredns:1.11.3
COPY --from=healthcheck /bin/busybox /bin/busybox
