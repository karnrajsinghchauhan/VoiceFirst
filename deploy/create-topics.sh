#!/usr/bin/env bash
# Creates the six topics with the retention in contracts/kafka-topics.md. Idempotent.
set -euo pipefail
B="-X brokers=redpanda:9092"
create() {
  rpk topic create "$1" -c "retention.ms=$2" $B || rpk topic alter-config "$1" --set "retention.ms=$2" $B
}
create av.booking-events.v1 604800000
create av.gate-decisions.v1 15552000000
create av.call-outcomes.v1 15552000000
create av.handoffs.v1 2592000000
create av.complaints.v1 31536000000
create av.audit.v1 15552000000
