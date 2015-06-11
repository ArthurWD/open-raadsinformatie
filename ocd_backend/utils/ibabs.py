import re
import datetime


def _ibabs_to_dict(o, fields):
    """
    Converts an iBabs SOAP response to a JSON serializable dict
    """
    output = {}
    for f in fields.keys():
        v = getattr(o, f)
        if fields[f] is not None:
            if v is not None:
                output[f] = fields[f](v)
            else:
                output[f] = v
        else:
            output[f] = v
    return output


def document_to_dict(d):
    """
    Converts an iBabsDocument SOAP response to a JSON serializable dict
    """
    fields = {
        'Id': lambda x: unicode(x),
        'FileName': lambda x: unicode(x),
        'DisplayName': lambda x: unicode(x),
        'Confidential': None,
        'PublicDownloadURL': lambda x: unicode(x),
        'FileSize': lambda x: int(x) if x is not None else None
    }
    return _ibabs_to_dict(d, fields)


def meeting_to_dict(m):
    """
    Converts an iBabsMeeting to a JSON serializable dict
    """
    # TODO: add list items?
    fields = {
        'Id': None,
        'MeetingtypeId': None,
        'MeetingDate': lambda x: x.isoformat(),
        'StartTime': lambda x: unicode(x),
        'EndTime': lambda x: unicode(x),
        'Location': None,
        'Chairman': None,
        'Explanation': None,
        'PublishDate': lambda x: x.isoformat(),
        'Documents': lambda x: [
            document_to_dict(y) if y is not None else [] for y in x[0]]
    }
    return _ibabs_to_dict(m, fields)


def meeting_item_to_dict(m):
    """
    Converts an iBabsMeetingItem to a JSON serializable dict
    """
    fields = {
        'Id': None,
        'Features': None,
        'Title': None,
        'Explanation': None,
        'Confidential': None,
        'Documents': lambda x: [
            document_to_dict(y) if y is not None else [] for y in x[0]]
    }
    return _ibabs_to_dict(m, fields)

# json.dumps(meeting_to_dict(m.Meetings[0][0]))
