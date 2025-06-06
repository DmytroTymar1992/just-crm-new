from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import generate_task_for_interaction
from chats.models import Interaction

@receiver(post_save, sender=Interaction, dispatch_uid="interaction_auto_task")
def trigger_auto_task(sender, instance: Interaction, created, **kwargs):
    if not created:
        return
    # якщо потрібно обмежити типи — розкоментуйте ↓
    # if instance.interaction_type not in (
    #     Interaction.InteractionType.CALL,
    #     Interaction.InteractionType.EMAIL,
    #     Interaction.InteractionType.TELEGRAM,
    #     Interaction.InteractionType.VIBER,
    # ):
    #     return
    generate_task_for_interaction.delay(instance.pk)
