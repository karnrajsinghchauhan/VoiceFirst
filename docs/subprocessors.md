# Subprocessors (REQ-DPDP-09)

Data residency is India by default. The production config validator refuses to
boot unless every provider role declares a region inside Agoda's allowlist
(`AV_RESIDENCY__ALLOWED_REGIONS`, [CD]; default `in`).

| Role | Provider (config value) | Processing region | Data it sees | Status |
|------|-------------------------|-------------------|--------------|--------|
| stt | sarvam | India [CD: confirm] | Call audio (8 kHz) | Not contracted |
| stt | elevenlabs | Outside India [CD] | Call audio | Not built |
| stt | selfhosted (IndicConformer) | Agoda private cloud | Call audio | Not built; licence [CD] |
| tts | sarvam_bulbul | India [CD: confirm] | Agent text (redacted) | Not contracted |
| tts | elevenlabs | Outside India [CD] | Agent text | Not built |
| tts | selfhosted (Indic Parler-TTS / IndicF5) | Agoda private cloud | Agent text | Not built; licence [CD] |
| llm | openai | Outside India unless an India region is contracted [CD] | Redacted transcript, purpose-limited booking context | Not contracted |
| llm | anthropic | Outside India unless an India region is contracted [CD] | Redacted transcript, purpose-limited booking context | Not contracted |
| llm | vllm | Agoda private cloud | Redacted transcript | Not built |
| telephony | plivo | India PoP [CD] | Numbers, call audio in transit | Not contracted |
| telephony | exotel | India | Numbers, call audio in transit | Not built |
| whatsapp | meta_cloud_api | Outside India (Meta) [CD] | Number, template params | Not contracted |
| crm | zendesk | Agoda's Zendesk tenant region [CD] | Handoff summary, masked booking ref | Adapter built, not connected |
| crm | salesforce / hubspot | [CD] | Handoff summary | Not built |

No provider may train or fine-tune on client data (P4); this is a contract term
to include in every DPA.
