"""Policy model."""

from datetime import datetime, timezone
import mongoengine as me


class Policy(me.Document):
    """Policy table."""
    meta = {'collection': 'policies'}

    name = me.StringField(max_length=255, required=True)
    version = me.IntField(default=1, required=True)
    is_active = me.BooleanField(default=True, required=True)
    uploaded_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    extracted_text = me.StringField(null=True)  # full policy text for RAG

    # ZIP upload tracking
    source_zip = me.StringField(max_length=512, null=True)   # original ZIP filename
    storage_path = me.StringField(max_length=1024, null=True) # Supabase Storage path
    
    # In MongoEngine, we can either use a ListField(ReferenceField(Rule)) or
    # let Rule point back to Policy. Pointing back to Policy is usually better 
    # for large numbers of rules. We won't use cascade here since we can manually
    # delete rules or use a pre_delete signal if needed.
