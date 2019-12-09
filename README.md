## Build Docker image

```sh
$ docker build -t shidaqiu/istio-trans-analysis:0.1 .
```

## How to use it

```sh
$ mkdir -p workspace/config workspace/data workspace/output
$ cp config/config.yaml workspace/config/
$ cd workspace
$ docker run -it \
    -v $(pwd)/config:/trans_analysis/config \
    -v $(pwd)/data:/trans_analysis/data \
    -v $(pwd)/output:/trans_analysis/output \
    shidaqiu/istio-trans-analysis:0.1
```

The generated charts will be put in `workspace/output` dir.
