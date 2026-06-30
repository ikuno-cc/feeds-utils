from fastapi import APIRouter, HTTPException

from app.schemas.requests import CleanRequest, NormalizeRequest
from app.schemas.responses import CleanResponse, NormalizeResponse
from app.services.cleaner import CleanerOptions, clean
from app.services.normalizer import NormalizerOptions, normalize

router = APIRouter(prefix="/api/v1")


@router.post("/clean", response_model=CleanResponse, summary="Clean article text")
def clean_endpoint(req: CleanRequest):
    try:
        opts = CleanerOptions(
            fix_encoding=req.fix_encoding,
            extract_article=req.extract_article,
            strip_html=req.strip_html,
            strip_scripts=req.strip_scripts,
            strip_styles=req.strip_styles,
            decode_entities=req.decode_entities,
            normalize_unicode=req.normalize_unicode,
            remove_urls=req.remove_urls,
            remove_emails=req.remove_emails,
            remove_phones=req.remove_phones,
            remove_emojis=req.remove_emojis,
            transliterate=req.transliterate,
            remove_extra_whitespace=req.remove_extra_whitespace,
            collapse_repeated_punctuation=req.collapse_repeated_punctuation,
        )
        result = clean(req.text, opts)
        original_len = len(req.text)
        cleaned_len = len(result)
        return CleanResponse(
            cleaned=result,
            original_length=original_len,
            cleaned_length=cleaned_len,
            chars_removed=original_len - cleaned_len,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/normalize", response_model=NormalizeResponse, summary="Normalize text")
def normalize_endpoint(req: NormalizeRequest):
    try:
        opts = NormalizerOptions(
            lowercase=req.lowercase,
            unicode_form=req.unicode_form,
            collapse_whitespace=req.collapse_whitespace,
            strip_punctuation=req.strip_punctuation,
            strip_numbers=req.strip_numbers,
            normalize_quotes=req.normalize_quotes,
            normalize_dashes=req.normalize_dashes,
            normalize_ellipsis=req.normalize_ellipsis,
            normalize_spaces_around_punctuation=req.normalize_spaces_around_punctuation,
        )
        result = normalize(req.text, opts)
        original_len = len(req.text)
        normalized_len = len(result)
        return NormalizeResponse(
            normalized=result,
            original_length=original_len,
            normalized_length=normalized_len,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
