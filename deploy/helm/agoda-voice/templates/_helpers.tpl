{{- define "av.labels" -}}
app.kubernetes.io/name: agoda-voice
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end -}}

{{- define "av.env" -}}
- name: AV_ENVIRONMENT
  value: {{ .Values.environment | quote }}
- name: AV_TENANT_ID
  value: {{ .Values.tenantId | quote }}
- name: AV_BUS
  value: kafka
- name: AV_KAFKA_BOOTSTRAP
  value: {{ .Values.kafka.bootstrap | quote }}
- name: AV_STT
  value: {{ .Values.providers.stt | quote }}
- name: AV_TTS
  value: {{ .Values.providers.tts | quote }}
- name: AV_LLM
  value: {{ .Values.providers.llm | quote }}
- name: AV_TELEPHONY
  value: {{ .Values.providers.telephony | quote }}
- name: AV_WHATSAPP
  value: {{ .Values.providers.whatsapp | quote }}
- name: AV_CRM
  value: {{ .Values.providers.crm | quote }}
- name: AV_RESIDENCY
  value: {{ dict "allowed_regions" .Values.residency.allowedRegions "provider_regions" .Values.residency.providerRegions | toJson | quote }}
- name: AV_RETENTION
  value: {{ dict "audio_days" .Values.retention.audioDays "transcript_days" .Values.retention.transcriptDays "ict_log_days" .Values.retention.ictLogDays | toJson | quote }}
- name: AV_NTP_SERVERS
  value: {{ .Values.time.ntpServers | toJson | quote }}
- name: AV_DATABASE_URL
  valueFrom:
    secretKeyRef: {name: {{ .Values.postgres.existingSecret }}, key: {{ .Values.postgres.secretKey }}}
envFrom:
  - secretRef:
      name: {{ .Values.secrets.existingSecret }}
{{- end -}}
