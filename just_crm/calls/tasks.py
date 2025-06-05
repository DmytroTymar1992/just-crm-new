from celery import shared_task
from .models import Call
from deepgram import DeepgramClient, PrerecordedOptions
import requests
import logging
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

@shared_task
def transcribe_call(call_id, recording_link):
    """Transcribes a call recording and notifies the chat via WebSocket."""
    call = Call.objects.get(id=call_id)
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
            call.description = f"{call.description or ''}\nFailed to download audio for transcription: HTTP {response.status_code}"
            call.save()
            return
        source = {"buffer": response.content, "mimetype": "audio/mp3"}
        logger.debug(f"Sending audio to Deepgram for call ID {call_id}")
        transcription_response = deepgram.listen.prerecorded.v("1").transcribe_file(
            source, options
        )
        transcript = transcription_response["results"]["channels"][0]["alternatives"][0]["transcript"]
        if transcript:
            call.description = f"{call.description or ''}\nTranscription: {transcript}"
            call.save()
            logger.info(f"Transcription added for call ID {call_id}")
        else:
            call.description = f"{call.description or ''}\nNo transcription available"
            call.save()
            logger.warning(f"No transcription returned for call ID {call_id}")

    except Exception as e:
        logger.error(
            f"Deepgram transcription failed for call ID {call_id}: {str(e)}",
            exc_info=True,
        )
        call.description = f"{call.description or ''}\nTranscription error: {str(e)}"
        call.save()
    finally:

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{call.interaction.chat_id}",
            {
                "type": "open_call_result_modal",
                "call_id": call.id,
                "description": call.description or "",
            },
        )
        logger.info(
            f"Sent open_call_result_modal for call ID {call.id} with description"
        )