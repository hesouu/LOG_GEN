# -*- coding: utf-8 -*-
# 이 파일이 UTF-8 인코딩을 사용한다는 것을 명시한다. 한글 주석과 문자열을 안전하게 처리하기 위한 설정이다.

"""PyFlink Silver streaming application.

Raw Kinesis -> PyFlink 정제 -> Silver Kinesis
Silver Kinesis -> Firehose -> S3 silver/
"""
# 위 모듈 설명은 이 애플리케이션의 전체 데이터 흐름을 요약한다.
# Bronze/Raw Kinesis의 데이터를 읽고 PyFlink에서 정제한 뒤 Silver Kinesis로 전달한다.
# 이후 Silver Kinesis의 데이터는 Firehose를 통해 S3의 silver/ 영역으로 적재된다.

from __future__ import annotations
# 타입 힌트를 현재 실행 시점에 즉시 평가하지 않고 지연 평가하도록 한다.
# Python 버전 간 타입 힌트 호환성을 높이고 불필요한 타입 평가 문제를 줄인다.

import json
# application_properties.json 파일을 Python 객체로 읽기 위해 표준 json 모듈을 사용한다.

import os
# 파일 경로 계산, 환경 변수 조회, 파일 존재 여부 확인 등을 위해 os 모듈을 사용한다.

from pyflink.table import DataTypes, EnvironmentSettings, TableEnvironment
# DataTypes는 Python UDF의 반환 타입 등 Flink SQL/Table API의 데이터 타입을 정의할 때 사용한다.
# EnvironmentSettings는 Flink TableEnvironment를 Streaming 모드로 생성하기 위한 설정 객체다.
# TableEnvironment는 SQL/Table API를 실행하고 Source/Sink 테이블을 등록하는 핵심 실행 환경이다.

from pyflink.table.udf import udf
# 일반 Python 함수를 Flink SQL에서 호출 가능한 UDF(User Defined Function)로 등록하기 위해 사용한다.

from transform import clean_event_payload
# 실제 JSON 정제 규칙은 transform.py에 분리되어 있으며 이 함수를 호출해 Bronze 데이터를 Silver 형태로 변환한다.


MANAGED_PROPERTIES_PATH = "/etc/flink/application_properties.json"
# AWS Managed Service for Apache Flink 환경에서 Runtime Property 파일이 제공되는 기본 경로를 상수로 정의한다.

IS_LOCAL = bool(os.environ.get("IS_LOCAL"))
# IS_LOCAL 환경 변수가 존재하면 True로 처리하여 로컬 실행과 AWS Managed Flink 실행을 구분한다.
# 예: IS_LOCAL=1 로 실행하면 로컬 모드가 된다.


@udf(result_type=DataTypes.STRING())
# 아래 clean_event 함수를 Flink SQL에서 호출할 수 있는 Python UDF로 변환한다.
# result_type=STRING은 이 함수가 정제된 JSON 문자열 또는 NULL을 반환한다는 의미다.
def clean_event(payload: str):
    # Flink SQL에서 전달받은 STRING payload를 인자로 받는다.

    """Flink SQL에서 호출하는 Python UDF."""
    # 이 함수는 Flink SQL과 transform.py의 정제 로직 사이를 연결하는 래퍼 역할을 한다.

    return clean_event_payload(payload)
    # 실제 정제는 transform.py의 clean_event_payload()에 위임하고 그 결과를 그대로 반환한다.


def _project_dir() -> str:
    # 현재 실행 중인 파일 위치를 기준으로 프로젝트의 flink 디렉터리 경로를 계산하는 보조 함수다.

    """로컬에서는 flink/ 디렉터리, 배포 ZIP에서는 현재 디렉터리를 반환."""
    # 로컬 구조와 AWS 배포 ZIP 구조가 다를 수 있기 때문에 공통 기준 경로를 계산한다.

    current_dir = os.path.dirname(os.path.realpath(__file__))
    # __file__의 실제 절대 경로를 구한 뒤 현재 main.py가 위치한 디렉터리 경로만 추출한다.

    if os.path.basename(current_dir) == "app":
        # 현재 파일이 flink/app/main.py 구조에 있다면 현재 디렉터리 이름은 app이 된다.

        return os.path.dirname(current_dir)
        # app의 상위 디렉터리인 flink/를 프로젝트 기준 경로로 반환한다.

    return current_dir
    # 배포 ZIP처럼 main.py가 루트에 위치한다면 현재 디렉터리 자체를 프로젝트 기준 경로로 반환한다.


def _property_map(properties: list[dict], group_id: str) -> dict:
    # application_properties.json의 여러 Property Group 중 원하는 그룹의 PropertyMap만 추출한다.

    for prop in properties:
        # Runtime Property 목록을 하나씩 순회한다.

        if prop.get("PropertyGroupId") == group_id:
            # 현재 Property Group의 ID가 찾고 있는 group_id와 같은지 확인한다.

            return prop.get("PropertyMap", {})
            # 일치하면 해당 그룹의 실제 설정값인 PropertyMap을 반환한다.
            # PropertyMap이 없다면 빈 dict를 기본값으로 반환한다.

    raise RuntimeError(f"Runtime property group not found: {group_id}")
    # 끝까지 찾지 못했다면 잘못된 배포 설정이므로 즉시 RuntimeError를 발생시킨다.


def _load_application_properties() -> list[dict]:
    # 로컬 또는 AWS Managed Flink 환경에 맞는 application_properties.json을 읽어 반환한다.

    if IS_LOCAL:
        # 로컬 실행 모드인지 확인한다.

        path = os.path.join(_project_dir(), "application_properties.json")
        # 로컬에서는 flink/application_properties.json 파일을 사용한다.

    else:
        # IS_LOCAL이 설정되지 않았다면 AWS Managed Flink 환경으로 간주한다.

        path = MANAGED_PROPERTIES_PATH
        # AWS Managed Flink가 제공하는 /etc/flink/application_properties.json 경로를 사용한다.

    if not os.path.isfile(path):
        # 계산된 설정 파일이 실제 파일인지 확인한다.

        raise RuntimeError(f"Application properties file not found: {path}")
        # 설정 파일이 없으면 Kinesis ARN/Region 등을 알 수 없으므로 실행을 중단한다.

    with open(path, "r", encoding="utf-8") as file:
        # 설정 파일을 UTF-8 텍스트 읽기 모드로 연다.
        # with 문을 사용하면 작업이 끝난 뒤 파일이 자동으로 닫힌다.

        return json.load(file)
        # JSON 내용을 Python list/dict 객체로 변환하여 호출한 쪽에 반환한다.


def _create_table_environment() -> TableEnvironment:
    # PyFlink SQL/Table API가 실행될 Streaming TableEnvironment를 생성한다.

    settings = EnvironmentSettings.in_streaming_mode()
    # 유한한 Batch가 아니라 계속 들어오는 이벤트를 처리하는 Streaming 모드 설정을 생성한다.

    table_env = TableEnvironment.create(settings)
    # 위 Streaming 설정을 사용하여 Flink TableEnvironment를 실제로 만든다.

    # AWS Managed Flink에서는 Terraform Runtime Property의 jarfile 설정을 통해 Connector JAR을 로딩한다.
    # 따라서 AWS 환경에서는 애플리케이션 코드에서 직접 JAR 경로를 등록하지 않는다.
    # 반면 로컬 PyFlink 실행에서는 Kinesis Connector가 기본 포함되지 않으므로 Fat JAR을 직접 등록해야 한다.
    if IS_LOCAL:
        # 현재 로컬 실행 모드인 경우에만 로컬 Connector JAR 등록 절차를 수행한다.

        jar_path = os.path.join(_project_dir(), "target", "pyflink-dependencies.jar")
        # Maven 빌드 결과로 생성되는 Kinesis Connector 포함 Fat JAR의 예상 경로를 만든다.

        if not os.path.isfile(jar_path):
            # Maven 빌드 결과 파일이 실제로 존재하는지 확인한다.

            raise RuntimeError(
                # Connector JAR이 없으면 Kinesis 테이블 생성 시 connector 클래스를 찾을 수 없으므로 명확한 오류를 발생시킨다.

                "Connector JAR not found. Run 'mvn clean package' in the flink directory first."
                # 사용자에게 flink 디렉터리에서 Maven 패키징을 먼저 수행하라고 안내한다.
            )
            # RuntimeError 생성 표현식을 닫는다.

        jar_uri = "file:///" + jar_path.replace("\\", "/")
        # Flink pipeline.jars 설정은 URI 형식을 사용하므로 Windows의 역슬래시를 슬래시로 바꾸고 file:/// 접두사를 붙인다.

        table_env.get_config().get_configuration().set_string("pipeline.jars", jar_uri)
        # 생성한 Connector Fat JAR URI를 Flink의 pipeline.jars 설정에 등록한다.
        # 이후 CREATE TABLE ... connector='kinesis'를 실행할 때 해당 JAR의 Connector 클래스를 사용할 수 있다.

    return table_env
    # 설정이 끝난 TableEnvironment를 main() 함수에 반환한다.


def main() -> None:
    # 애플리케이션 실행의 시작점이며 Source 생성 → 정제 → Sink 전송까지 전체 흐름을 구성한다.

    table_env = _create_table_environment()
    # Streaming 모드의 Flink TableEnvironment를 생성한다.

    properties = _load_application_properties()
    # 로컬 또는 AWS 환경의 application_properties.json 설정값을 읽는다.

    input_props = _property_map(properties, "InputStream")
    # Runtime Property에서 Bronze/Raw 입력 Kinesis 설정 그룹인 InputStream0을 가져온다.

    output_props = _property_map(properties, "OutputStream")
    # Runtime Property에서 Silver 출력 Kinesis 설정 그룹인 OutputStream0을 가져온다.

    input_stream_arn = input_props["stream.arn"]
    # 입력 Kinesis Data Stream의 ARN을 읽는다.
    # 이 스트림은 로그 생성기가 데이터를 전송하는 Bronze/Raw Kinesis Stream이다.

    input_region = input_props["aws.region"]
    # 입력 Kinesis Stream이 존재하는 AWS Region을 읽는다.

    input_init_position = input_props.get("flink.source.init.position", "LATEST")
    # Flink가 Kinesis 데이터를 어느 위치부터 읽을지 설정한다.
    # Runtime Property에 값이 없으면 기본적으로 LATEST, 즉 Flink 실행 이후 새로 들어오는 레코드부터 읽는다.

    output_stream_arn = output_props["stream.arn"]
    # 정제 결과를 기록할 Silver Kinesis Data Stream ARN을 읽는다.

    output_region = output_props["aws.region"]
    # Silver Kinesis Stream이 존재하는 AWS Region을 읽는다.

    table_env.create_temporary_system_function("clean_event", clean_event)
    # Python 함수 clean_event를 Flink SQL에서 clean_event(...) 이름으로 사용할 수 있도록 등록한다.
    # temporary system function이므로 현재 Flink Job 실행 동안만 존재한다.

    # ------------------------------------------------------------------
    # Source: 기존 Raw/Bronze Kinesis Stream
    # ------------------------------------------------------------------
    # 입력 데이터의 도메인이 ecommerce/finance/game/smartfactory처럼 서로 다른 JSON 구조를 가질 수 있다.
    # 따라서 여기서 도메인별 컬럼 스키마를 고정하지 않고 레코드 전체를 STRING payload 하나로 받는다.
    # 'format'='raw'를 사용하면 Kinesis 레코드 값을 그대로 문자열 형태로 전달할 수 있다.
    table_env.execute_sql(
        # Flink SQL DDL을 실행하여 Bronze Kinesis Stream을 raw_stream이라는 논리 테이블로 등록한다.

        f"""
        CREATE TABLE raw_stream (
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
        # CREATE TABLE은 실제 데이터를 복사하지 않는다.
        # raw_stream이라는 Table API 이름과 실제 Kinesis Stream 사이의 연결 정보를 Flink에 등록한다.
        # payload STRING: Kinesis 레코드 전체를 하나의 문자열 컬럼으로 취급한다.
        # connector='kinesis': 이 테이블의 실제 데이터 소스가 Amazon Kinesis임을 지정한다.
        # stream.arn: 읽을 Kinesis Stream을 ARN으로 지정한다.
        # aws.region: Kinesis API를 호출할 AWS Region을 지정한다.
        # source.init.position: LATEST/TRIM_HORIZON 등의 최초 읽기 위치를 지정한다.
        # format='raw': Kinesis 레코드 값을 별도 JSON 스키마 해석 없이 그대로 payload에 넣는다.
    )
    # Source 테이블 등록 SQL 실행 호출을 종료한다.

    # ------------------------------------------------------------------
    # Sink: Flink 정제 결과를 저장할 Silver Kinesis Stream
    # ------------------------------------------------------------------
    # 정제된 결과 역시 JSON 문자열 하나이므로 payload STRING 단일 컬럼 구조를 사용한다.
    table_env.execute_sql(
        # Flink SQL DDL을 실행하여 Silver Kinesis Stream을 silver_stream이라는 Sink 테이블로 등록한다.

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
        # silver_stream 역시 논리 테이블이며 실제 데이터는 지정된 Kinesis Stream으로 기록된다.
        # payload STRING: 정제 완료된 JSON 문자열을 단일 컬럼으로 받는다.
        # connector='kinesis': 출력 대상이 Amazon Kinesis임을 지정한다.
        # stream.arn: 정제 결과를 쓸 Silver Kinesis Stream ARN을 지정한다.
        # aws.region: 출력 Kinesis Stream의 Region을 지정한다.
        # sink.batch.max-size='100': 최대 100개 레코드를 묶어 Sink 전송할 수 있도록 배치 크기를 지정한다.
        # format='raw': payload 문자열을 그대로 Kinesis 레코드 값으로 기록한다.
    )
    # Sink 테이블 등록 SQL 실행 호출을 종료한다.

    # ------------------------------------------------------------------
    # Bronze -> Silver 변환 및 전송
    # ------------------------------------------------------------------
    # raw_stream에서 payload를 읽는다.
    # Python UDF clean_event(payload)를 적용하여 transform.py의 정제 규칙을 실행한다.
    # JSON 파싱 실패, JSON Object가 아닌 데이터 등은 clean_event가 None을 반환한다.
    # Flink SQL에서는 Python None이 SQL NULL로 변환된다.
    # WHERE cleaned_payload IS NOT NULL 조건을 이용하여 잘못된 데이터는 Silver Stream에 넣지 않는다.
    # 정상적으로 정제된 JSON 문자열만 silver_stream으로 INSERT한다.
    result = table_env.execute_sql(
        # 아래 INSERT INTO SQL을 실행하면 실제 Streaming Job이 시작된다.

        """
        INSERT INTO silver_stream
        SELECT cleaned_payload
        FROM (
            SELECT clean_event(payload) AS cleaned_payload
            FROM raw_stream
        )
        WHERE cleaned_payload IS NOT NULL
        """
        # 내부 SELECT: raw_stream의 각 payload에 clean_event UDF를 적용한다.
        # AS cleaned_payload: UDF 결과에 cleaned_payload라는 임시 컬럼명을 붙인다.
        # 외부 SELECT: 정제 결과 컬럼만 선택한다.
        # WHERE ... IS NOT NULL: 정제 실패 레코드를 제외한다.
        # INSERT INTO silver_stream: 살아남은 정제 레코드를 Silver Kinesis로 지속 전송한다.
    )
    # execute_sql()이 반환한 TableResult를 result 변수에 저장한다.

    if IS_LOCAL:
        # AWS Managed Flink에서는 서비스가 Job 수명주기를 관리하므로 별도의 wait가 필요하지 않다.
        # 로컬 standalone 실행에서는 Python 메인 프로세스가 끝나면 Job이 종료될 수 있으므로 대기한다.

        result.wait()
        # Streaming Job이 종료될 때까지 현재 Python 프로세스를 블로킹하여 계속 실행 상태로 유지한다.


if __name__ == "__main__":
    # 이 파일이 import된 것이 아니라 python main.py처럼 직접 실행된 경우에만 아래 main()을 호출한다.

    main()
    # 위에서 정의한 PyFlink Streaming 애플리케이션을 실제로 시작한다.
