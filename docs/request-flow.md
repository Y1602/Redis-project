# 请求处理流程

## 1. 输入数据
每次模拟一条访问请求，包含以下字段：
ip、time、method、path、status
示例-156.195.148.16 - - [27/Apr/2026:09:49:50 +0000] "GET /login HTTP/1.1" 200 896 "-" "curl/8.18.0"

## 2. 请求处理流程

接收访问日志  
        ↓  
解析日志，提取 ip/time/method/path/status  
        ↓  
检查 ban:ip:{ip}  
        ↓  
如果已封禁，输出blocked，并结束流程  
        ↓  
更新访问次数ip:{ip}:count:{date}  
        ↓  
更新 IP 信息ip:{ip}:info  
        ↓  
记录最近访问日志ip:{ip}:logs  
        ↓  
加入当天活跃IP集合 active:ip:{date}  
        ↓  
根据 path/status 计算本次风险分  
        ↓  
更新风险排行榜 risk:rank:{date}  
        ↓  
获取该 IP 当天累计风险分  
        ↓  
如果风险分 >= 阈值，写入 ban:ip:{ip} 并设置 TTL  
        ↓  
输出处理结果  

## 3. 关键处理逻辑

### 3.1 检查是否封禁
	GET ban:ip:{ip} 如果存在则blocked；不存在则继续处理

### 3.2 更新访问次数
	INCR ip:{ip}:count:{date}

### 3.3 更新IP信息
	首次访问：HSETNX ip:{ip}:info first_seen {time}
	每次访问更新：HSET ip:{ip}:info last_seen {time} last_path {path} last_status {status}

### 3.4 记录最近访问日志
	LPUSH ip:{ip}:logs "{time} {method} {path} {status}"
	LTRIM ip:{ip}:logs 0 9 

### 3.5 记录活跃IP
	SADD active:ip:{date} {ip}

### 3.6 更新风险排行榜
	ZINCRBY risk:rank:{date} {score} {ip}

### 3.7 判断是否封禁
	ZSCORE risk:rank:{date} {ip}
	如果风险值达到阈值：SET ban:ip:{ip} 1 EX 60

## 4. 预期效果
	项目可以完成：
	    1. 解析访问日志
	    2. 记录IP访问次数
	    3. 记录IP基础信息
    	4. 保存最近访问日志
	    5. 统计当天活跃IP
	    6. 维护风险排行榜
	    7. 自动临时封禁高风险IP 
