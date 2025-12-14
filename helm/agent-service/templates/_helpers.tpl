{{/*
Expand the name of the chart.
*/}}
{{- define "agent-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "agent-service.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "agent-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "agent-service.labels" -}}
helm.sh/chart: {{ include "agent-service.chart" . }}
{{ include "agent-service.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: agent-service
environment: {{ .Values.global.environment }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "agent-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agent-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API specific labels
*/}}
{{- define "agent-service.apiLabels" -}}
{{ include "agent-service.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "agent-service.apiSelectorLabels" -}}
{{ include "agent-service.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Worker specific labels
*/}}
{{- define "agent-service.workerLabels" -}}
{{ include "agent-service.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Worker selector labels
*/}}
{{- define "agent-service.workerSelectorLabels" -}}
{{ include "agent-service.selectorLabels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Beat specific labels
*/}}
{{- define "agent-service.beatLabels" -}}
{{ include "agent-service.labels" . }}
app.kubernetes.io/component: beat
{{- end }}

{{/*
Beat selector labels
*/}}
{{- define "agent-service.beatSelectorLabels" -}}
{{ include "agent-service.selectorLabels" . }}
app.kubernetes.io/component: beat
{{- end }}

{{/*
Flower specific labels
*/}}
{{- define "agent-service.flowerLabels" -}}
{{ include "agent-service.labels" . }}
app.kubernetes.io/component: flower
{{- end }}

{{/*
Flower selector labels
*/}}
{{- define "agent-service.flowerSelectorLabels" -}}
{{ include "agent-service.selectorLabels" . }}
app.kubernetes.io/component: flower
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "agent-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "agent-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the image path
*/}}
{{- define "agent-service.image" -}}
{{- $registryName := .Values.image.registry -}}
{{- $repositoryName := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" .Values.global.imageRegistry $repositoryName $tag -}}
{{- else }}
{{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- end }}
{{- end }}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "agent-service.imagePullSecrets" -}}
{{- if .Values.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.imagePullSecrets }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create the name of the config map
*/}}
{{- define "agent-service.configMapName" -}}
{{- printf "%s-config" (include "agent-service.fullname" .) }}
{{- end }}

{{/*
Create the name of the secret
*/}}
{{- define "agent-service.secretName" -}}
{{- if .Values.secret.useExisting }}
{{- .Values.secret.existingSecretName }}
{{- else }}
{{- printf "%s-secret" (include "agent-service.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Common environment variables
*/}}
{{- define "agent-service.commonEnv" -}}
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: POD_NAMESPACE
  valueFrom:
    fieldRef:
      fieldPath: metadata.namespace
- name: POD_IP
  valueFrom:
    fieldRef:
      fieldPath: status.podIP
- name: NODE_NAME
  valueFrom:
    fieldRef:
      fieldPath: spec.nodeName
{{- end }}

{{/*
Validate required values
*/}}
{{- define "agent-service.validateValues" -}}
{{- if and .Values.secret.enabled (not .Values.secret.useExisting) }}
  {{- if not .Values.secret.data.DATABASE_URL }}
    {{- fail "DATABASE_URL is required in secret.data when secret is enabled" }}
  {{- end }}
  {{- if not .Values.secret.data.SECRET_KEY }}
    {{- fail "SECRET_KEY is required in secret.data when secret is enabled" }}
  {{- end }}
{{- end }}
{{- end }}
