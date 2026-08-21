# PyFlink Silver Processor

구조:

```text
Raw Kinesis
   ↓
Managed Service for Apache Flink (PyFlink)
   ↓
Silver Kinesis
   ↓
Amazon Data Firehose
   ↓
S3 silver/
```

## 빌드

```bash
mvn clean package
```

생성 파일:

```text
target/flink-silver.zip
target/pyflink-dependencies.jar
```

`flink-silver.zip` 내부에는 다음 파일이 포함된다.

```text
main.py
transform.py
lib/pyflink-dependencies.jar
```

## 로컬 PyFlink 실행(선택)

Python 3.11 환경에서:

```bash
pip install apache-flink==1.20.0
```

`application_properties.json`의 Stream ARN을 실제 값으로 수정한 뒤:

Linux/macOS:

```bash
export IS_LOCAL=true
python app/main.py
```

Windows CMD:

```bat
set IS_LOCAL=true
python app\main.py
```
