import datetime
import json
import logging
import os


def init_logger(job_id, execution_id, host, host_id):
    date_dir = datetime.datetime.now().strftime('%Y%m%d')
    base_dir = '/fap/logs/ansible'
    log_dir = os.path.join(base_dir, date_dir)
    os.makedirs(log_dir, exist_ok=True)
    safe_host = (host or 'nohost').replace(':', '_').replace('/', '_')
    safe_job = str(job_id) if job_id is not None else 'nojob'
    safe_exec = str(execution_id) if execution_id is not None else 'noexec'
    log_path = os.path.join(
        log_dir,
        f'job-{safe_job}_exec-{safe_exec}_host-{safe_host}.log',
    )

    logger = logging.getLogger('inspection_runner')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def log_result_json(logger, res):
    logger.info(
        '    result_json=\n%s',
        json.dumps(res, ensure_ascii=False, indent=2),
    )


def log_item_start(
    logger,
    code,
    item_id,
    module_source,
    method,
    connection_credential,
    item_payload,
    module_key,
    app_credential,
    common_token,
):
    logger.info(
        '--- item start: inspection_code=%s item_id=%s source=%s method=%s conn_credential=%s req_app_type=%s req_app=%s req_app_version=%s matched_app_type=%s matched_app=%s matched_app_version=%s app_id=%s app_credential=%s',
        code,
        item_id,
        module_source or 'none',
        method,
        'yes' if connection_credential else 'no',
        (item_payload or {}).get('application_type_name'),
        (item_payload or {}).get('application_name'),
        (item_payload or {}).get('application_family_name'),
        module_key[1] if module_key else common_token,
        module_key[2] if module_key else common_token,
        module_key[3] if module_key else common_token,
        (item_payload or {}).get('application_id'),
        'yes' if app_credential else 'no',
    )


def log_runner_terminated(logger, total_count, failed_count):
    logger.info('### Runner terminated. total=%s failed=%s', total_count, failed_count)


def log_item_result_summary(logger, code, res, summarize_result_func):
    summary = summarize_result_func(res)
    logger.info(
        '--- item done: inspection_code=%s status=%s error=%s reasons=%s raw_len=%s',
        code,
        summary.get('status'),
        summary.get('error'),
        summary.get('reasons'),
        summary.get('raw_len'),
    )
    if summary.get('message'):
        logger.info('    message=%s', summary.get('message'))
    if summary.get('metrics'):
        logger.info('    metrics=%s', summary.get('metrics'))
    if summary.get('raw_preview'):
        logger.info('    raw_preview=%s', summary.get('raw_preview'))
    log_result_json(logger, res)

