# -*- coding: utf-8 -*-
# flink 앱 엔트리 포인트 (환경설정, 필요한 구성생성)

from __future__ import annotations
import json
import os
from pyflink.table import DataTypes, EnvironmentSettings, TableEnvironment
# 일반 파이썬 함수를 Flink SQL에서 호출 가능하게 등록 처리(UDF : User Defined Function)
from pyflink.table.udf import udf
# [REJECT]
from transform import clean_event_payload,reject_event_payload

# 테라폼이 인프라 구성시 자동으로 설정
MANAGED_PROPERTIES_PATH = "/etc/flink/application_properties.json"
IS_LOCAL = bool(os.environ.get("IS_LOCAL"))

# 결과는 문자열로 반환, clean_event라는 함수는 Flink에서 사용하는 SQL 내에서 사용 가능
@udf(result_type=DataTypes.STRING())
def clean_event(payload: str):
    # 정제, 전처리 전담 함수를 래핑
    return clean_event_payload(payload)

# [REJECT]
@udf(result_type=DataTypes.STRING())
def reject_event(payload: str):
    # 오염데이터 전담 함수를 래핑
    return reject_event_payload(payload)


# flink 경로 계산을 위한 함수
def _project_dir() -> str:
    current_dir = os.path.dirname(os.path.realpath(__file__))
    if os.path.basename(current_dir) == "app":
        return os.path.dirname(current_dir)
    return current_dir

# xxx.json 설정 파일에서 정보 획득용
def _property_map(properties: list[dict], group_id: str) -> dict:
    for prop in properties:
        if prop.get("PropertyGroupId") == group_id:
            return prop.get("PropertyMap", {})
    raise RuntimeError(f"Runtime property group not found: {group_id}")

# flink 구동 환경에 맞춰서 로컬 or 클라우드에서 정보 로드(json 파일)
def _load_application_properties() -> list[dict]:
    if IS_LOCAL:
        path = os.path.join(_project_dir(), "application_properties.json")
    else:
        path = MANAGED_PROPERTIES_PATH
    if not os.path.isfile(path):
        raise RuntimeError(f"Application properties file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

# Flink가 SQL/테이블 API들을 사용할 있는 스트리밍 모드의 환경구성
def _create_table_environment() -> TableEnvironment:
    # 스트리밍 모드 설정
    settings = EnvironmentSettings.in_streaming_mode()
    # 스트리밍 모드로 테이블환경 구성
    table_env = TableEnvironment.create(settings)
    # 로컬에서 구동시 jar 파일 등록
    # 배치 파일로 빌드시 자동으로 다운로드해서 zip으로 같이 넣어주는 파일임
    if IS_LOCAL:
        jar_path = os.path.join(_project_dir(), "target", "pyflink-dependencies.jar")
        if not os.path.isfile(jar_path):
            raise RuntimeError(
                "Connector JAR not found. Run 'mvn clean package' in the flink directory first."
            )
        jar_uri = "file:///" + jar_path.replace("\\", "/")
        table_env.get_config().get_configuration().set_string("pipeline.jars", jar_uri)
    return table_env

def main() -> None:
    # 순서대로 실행을 위한 절차 진행

    # 1. 스트리밍 모드의 flink  테이블환경(테이블구성, sql 사용) 구성
    table_env = _create_table_environment()
    # 2. application_properties.json(로컬), aws 환경등 정보 로드(설정값)->테라폼으로 구성시 자동생성
    properties = _load_application_properties()

    # 3. 런타임 속성에서 InputStream0 이름의 키네시스 정보 획득. 브론즈 입력
    input_props = _property_map(properties, "InputStream0")
    # 4. 런타임 속성에서 OutputStream0 이름의 키네시스 정보 획득. 실버 출력
    output_props = _property_map(properties, "OutputStream0")
    # [REJECT] 비정상 데이터 출력용 kinesis 설정
    reject_props = _property_map(properties, "RejectStream0")

    # 5. 키네시스 arn, 리전, 입력시 어디서부터 읽을 것인지 등 정보 로드
    input_stream_arn = input_props["stream.arn"]
    input_region = input_props["aws.region"]
    input_init_position = input_props.get("flink.source.init.position", "LATEST")
    output_stream_arn = output_props["stream.arn"]
    output_region = output_props["aws.region"]
    # [REJECT]
    reject_stream_arn = reject_props["stream.arn"]
    reject_region = reject_props["aws.region"]

    # 6. 파이썬 함수 clean_event를 Flink SQL 내부에서 clean_event(..)로 사용하도록 등록
    table_env.create_temporary_system_function("clean_event", clean_event)
    # [REJECT] reject_event 함수를 sql에서 사용할수 있게 등록
    table_env.create_temporary_system_function("reject_event", reject_event)

    # 7. Flink SQL 이용하여 데이터 실시간 처리, 입력데이터도 저장, 출력데이터도 저장=>테이블필요
    #    도메인별로 (json)구조가 상이할수 있으므로 => 통으로 문자열 받는 구성
    #    'format' = 'raw' : 저장되는 데이터의 스키마 해석없이 통으로 저장
    table_env.execute_sql(
        f"""
        CREATE TABLE bronze_stream (
            payload STRING
        )
        WITH (
            'connector' = 'kinesis',
            'stream.arn' = '{input_stream_arn}',
            'aws.region' = '{input_region}',
            'source.init.position' = '{input_init_position}',
            'format' = 'raw'
        )
        """
    )
    # 8. 정제된 결과도 도메인별로 상이 => json 형태 문자열 그대로 저장
    #    'sink.batch.max-size' = '100', : 최대 100개 레코드를 묶어서 처리 -> 조절가능(firehose)
    #    sink : 정제된 데이터를 kinesis 스트림으로 내보내는 단계
    table_env.execute_sql(
        f"""
        CREATE TABLE silver_stream (
            payload STRING
        )
        WITH (
            'connector' = 'kinesis',
            'stream.arn' = '{output_stream_arn}',
            'aws.region' = '{output_region}',
            'sink.batch.max-size' = '100',
            'format' = 'raw'
        )
        """
    )
    # [REJECT] 비정상(오염) 데이터용 kinesis sink, 테이블구성
    table_env.execute_sql(
        f"""
        CREATE TABLE rejected_stream (
            payload STRING
        )
        WITH (
            'connector' = 'kinesis',
            'stream.arn' = '{reject_stream_arn}',
            'aws.region' = '{reject_region}',
            'sink.batch.max-size' = '100',
            'format' = 'raw'
        )
        """
    )

    # [REJECT] 단일 insert 대신 정상/비정상 sink를 처리하는 하나의 job으로 StatementSet 구성
    statement_set = table_env.create_statement_set()

    # 9. bronze_stream -> 쿼리 -> 정제된 데이터 획득(cleaned_payload) 
    #    -> 체킹(실제 데이터가 있을때만) -> silver_stream 저장
    #    잘못된 데이터는 버림 => 왜 잘못된는가 분석 x (데이터가 오직 브로즈에만 남아 있음)
    #    향후 잘못 구성된 데이터만 모아서 추후 체크(배치 프로세싱 분석)
    #    브론즈 => 배치 프로세싱으로 추출하여도됨
    # [REJECT]
    #result = table_env.execute_sql(
    statement_set.add_insert_sql(
        """
        INSERT INTO silver_stream
        SELECT cleaned_payload
        FROM (
            SELECT clean_event(payload) AS cleaned_payload
            FROM bronze_stream
        )
        WHERE cleaned_payload IS NOT NULL
        """
    )
    # [REJECT] : 오염 데이터 저장, 오염데이터 검사 => 해당되는 데이터만 전송
    statement_set.add_insert_sql(
        """
        INSERT INTO rejected_stream
        SELECT rejected_payload
        FROM (
            SELECT reject_event(payload) AS rejected_payload
            FROM bronze_stream
        )
        WHERE rejected_payload IS NOT NULL
        """
    )
    # [REJECT] 두개의 sink를 병렬 처리
    result = statement_set.execute()

    # 로컬에서 flink 구동시 파이썬 앱 => 종료 처리때문에 강제 블럭(계속 작동되도록)
    if IS_LOCAL:
        result.wait()

if __name__ == "__main__":
    # 프로그램 시작점 -> main 함수 호출 하면서 실행 (함수지향적 프로그램)
    main()