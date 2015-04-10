
import forms
import models

########################## SPACES ##########################

# Mapping between access protocol and protocol specific fields
PROTOCOL = {
    models.Space.ARKIVUM: {
        'model': models.Arkivum,
        'form': forms.ArkivumForm,
        'fields': ['host',
                   'remote_user',
                   'remote_name']
    },
    models.Space.DURACLOUD: {
        'model': models.Duracloud,
        'form': forms.DuracloudForm,
        'fields': ['host', 'user', 'duraspace'],
    },
    models.Space.FEDORA: {
        'model': models.Fedora,
        'form': forms.FedoraForm,
        'fields': ['fedora_user',
                   'fedora_password',
                   'fedora_name']
    },
    # BUG: fields: [] works for obj_create, but includes everything in model_to_dict
    models.Space.LOCAL_FILESYSTEM: {
        'model': models.LocalFilesystem,
        'form': forms.LocalFilesystemForm,
        'fields': []
    },
    models.Space.LOM: {
        'model': models.Lockssomatic,
        'form': forms.LockssomaticForm,
        'fields': ['au_size',
                   'sd_iri',
                   'collection_iri',
                   'content_provider_id',
                   'external_domain',
                   'keep_local',
                   'checksum_type']
    },
    models.Space.NFS: {
        'model': models.NFS,
        'form': forms.NFSForm,
        'fields': ['manually_mounted',
                   'remote_name',
                   'remote_path',
                   'version']
    },
    models.Space.PIPELINE_LOCAL_FS: {
        'model': models.PipelineLocalFS,
        'form': forms.PipelineLocalFSForm,
        'fields': ['remote_user',
                   'remote_name']
    },
}
