# Generated Hayangi & Hadaengi Character Assets

Reference-based 2D PNG character assets for internal semiconductor AI newsletter drafts.
Source pose sheets are kept in `source/`; individual transparent PNG files are in `png/`.

## Pack

- Hayangi solo: 10 files named `hayangi_semicon_*`
- Hadaengi solo: 10 files named `hadaengi_semicon_*`
- Hayangi + Hadaengi duo: 10 files named `duo_semicon_*`

## PNG Assets

| asset_id | file | recommended roles |
| --- | --- | --- |
| `hayangi_semicon_hello` | `png/hayangi_semicon_hello.png` | cover, intro |
| `hayangi_semicon_chip_note` | `png/hayangi_semicon_chip_note.png` | tip, case, workflow |
| `hayangi_semicon_security_shield` | `png/hayangi_semicon_security_shield.png` | security, caution |
| `hayangi_semicon_prompt_magic` | `png/hayangi_semicon_prompt_magic.png` | tip, why |
| `hayangi_semicon_question` | `png/hayangi_semicon_question.png` | why, quiz, case |
| `hayangi_semicon_checklist` | `png/hayangi_semicon_checklist.png` | checklist, tip, recap |
| `hayangi_semicon_data_chart` | `png/hayangi_semicon_data_chart.png` | metric, case, recap |
| `hayangi_semicon_privacy_stop` | `png/hayangi_semicon_privacy_stop.png` | security, caution |
| `hayangi_semicon_thumbs_up` | `png/hayangi_semicon_thumbs_up.png` | recap, closing |
| `hayangi_semicon_calendar` | `png/hayangi_semicon_calendar.png` | closing, recap, cover |
| `hadaengi_semicon_hello` | `png/hadaengi_semicon_hello.png` | cover, intro |
| `hadaengi_semicon_laptop_helper` | `png/hadaengi_semicon_laptop_helper.png` | case, workflow, tip |
| `hadaengi_semicon_data_scan` | `png/hadaengi_semicon_data_scan.png` | case, metric, workflow |
| `hadaengi_semicon_workflow` | `png/hadaengi_semicon_workflow.png` | workflow, case, tip |
| `hadaengi_semicon_idea` | `png/hadaengi_semicon_idea.png` | why, tip, case |
| `hadaengi_semicon_toolbox` | `png/hadaengi_semicon_toolbox.png` | tip, workflow, checklist |
| `hadaengi_semicon_robot_chat` | `png/hadaengi_semicon_robot_chat.png` | tip, case, why |
| `hadaengi_semicon_chart_insight` | `png/hadaengi_semicon_chart_insight.png` | metric, recap, case |
| `hadaengi_semicon_search_lens` | `png/hadaengi_semicon_search_lens.png` | case, why, tip |
| `hadaengi_semicon_cta_arrow` | `png/hadaengi_semicon_cta_arrow.png` | closing, cta |
| `duo_semicon_welcome` | `png/duo_semicon_welcome.png` | cover, intro |
| `duo_semicon_chip_highfive` | `png/duo_semicon_chip_highfive.png` | cover, case, workflow |
| `duo_semicon_security_promise` | `png/duo_semicon_security_promise.png` | security, caution |
| `duo_semicon_quiz_answer` | `png/duo_semicon_quiz_answer.png` | why, case, recap |
| `duo_semicon_before_after` | `png/duo_semicon_before_after.png` | workflow, case |
| `duo_semicon_monthly_recap` | `png/duo_semicon_monthly_recap.png` | recap, metric |
| `duo_semicon_training_invite` | `png/duo_semicon_training_invite.png` | closing, cta, tip |
| `duo_semicon_download_ready` | `png/duo_semicon_download_ready.png` | closing, cta |
| `duo_semicon_data_pipeline` | `png/duo_semicon_data_pipeline.png` | workflow, case |
| `duo_semicon_lab_briefing` | `png/duo_semicon_lab_briefing.png` | case, closing, recap |

## Manifest

`generated_character_assets.local.json` contains base64 data URIs and role metadata for the 30 PNG assets above.
The `01-1 Decorative/Character Image Upload` node can read this file as the default character manifest.

## Validation

- All new PNG files are RGBA with transparent backgrounds.
- Each PNG was checked for a fully transparent 12px outer border.
- Extra transparent padding was added after cell cropping to avoid clipped ears, arms, tails, and props.

## Sticker Outline

The 30 semicon mascot PNG files use a white sticker-style outer border with a thin dark outer line, matching the cleaner legacy mascot cutout look. The manifest data URIs point to the outlined PNG files.
