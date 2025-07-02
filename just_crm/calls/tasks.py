from celery import shared_task
from .models import Call
from deepgram import DeepgramClient, PrerecordedOptions
import requests
import logging
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from ai_helper.tasks import generate_task_for_interaction
from ai_helper.tasks import analyze_transcription_result

logger = logging.getLogger(__name__)

@shared_task
def transcribe_call(call_id, recording_link):
    """Transcribes a call recording and notifies the chat via WebSocket."""
    call = Call.objects.get(id=call_id)
    instance = call.interaction
    try:
        logger.debug(
            f"Starting transcription for call ID {call_id}, recording_link: {recording_link}"
        )
        deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY)
        options = PrerecordedOptions(
            model="nova-2",
            language="uk",
            smart_format=True,
            punctuate=True,
            utterances=True,
        )
        logger.debug(f"Downloading audio from {recording_link}")
        response = requests.get(recording_link)
        logger.debug(f"Audio download response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(
                f"Failed to download audio for call ID {call_id}: {response.status_code}"
            )
            call.transcription = f"Failed to download audio for transcription: HTTP {response.status_code}"
            call.save()
            return
        source = {"buffer": response.content, "mimetype": "audio/mp3"}
        logger.debug(f"Sending audio to Deepgram for call ID {call_id}")
        transcription_response = deepgram.listen.prerecorded.v("1").transcribe_file(
            source, options
        )
        transcript = transcription_response["results"]["channels"][0]["alternatives"][0]["transcript"]
        if transcript:
            call.transcription = transcript
            call.save()
            logger.info(f"Transcription added for call ID {call_id}")
            analyze_transcription_result.delay(call.id)
            generate_task_for_interaction.delay(instance.pk)
        else:
            call.transcription = "No transcription available"
            call.result = "Невдала розмова"
            call.description = "Транскрипція не розпізнана або не містить мови"
            call.save()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{call.interaction.chat_id}",
                {
                    "type": "open_call_result_modal",
                    "call_id": call.id,
                    "result": call.result,
                    "description": call.description or "",
                    "loading": False
                },
            )
            logger.warning(f"No transcription returned for call ID {call_id}")

    except Exception as e:
        logger.error(
            f"Deepgram transcription failed for call ID {call_id}: {str(e)}",
            exc_info=True,
        )
        call.transcription = f"Transcription error: {str(e)}"
        call.result = "Невдала розмова"
        call.description = "Виникла помилка при обробці аудіо"
        call.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{call.interaction.chat_id}",
            {
                "type": "open_call_result_modal",
                "call_id": call.id,
                "result": call.result,
                "description": call.description or "",
                "loading": False
            },
        )

