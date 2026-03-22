# Typora Image Cloudreve Uploader

一个轻量的Python工具，用于将 [Cloudreve](https://cloudreve.org/) 网盘作为 [Typora](https://typora.io/) 的图床。支持多文件上传、事务回滚、直链生成以及本地映射记录。

## 快速开始

### 1. 下载与初始化

首次运行程序（双击或命令行运行），程序会在当前目录下自动生成 `conf` 文件夹和配置文件模板。

### 2. 配置文件
打开 `conf/config.json`，填入你的 Cloudreve 站点信息：

```json
{
    "api_url": "http://your-cloudreve-domain.com/api/v4",
    "email": "your-email@example.com",
    "password": "your-password",
    "remote_folder": "uploads/typora",
    "use_random_filename": true,
    "save_filename_mapping": true
}
```

### 3. Typora配置

图像配置中上传服务设置选择自定义命令，自定义命令填写exe文件所在路径

```shell
D:\tool\TyporaImageCloudreveUploader\TyporaImageCloudreveUploader.exe
```
