"""Cross-industry stress inputs; all content is explicitly simulated."""
import argparse
import json
from pathlib import Path


def examples():
    base={'footer':'模拟业务案例 · 用于验证内容自适应布局','assumptions':['全部内容为模拟示例，未经具体组织确认。']}
    teams=[
        ('课程设计与内容审核',['学习目标与分层课程设计','讲师资料审核及版权确认','课堂案例与课后练习制作','课程上线前的质量复核']),
        ('招生运营与学员服务',['招生渠道与报名转化分析','班级分配和开课通知','学习进度跟进与困难支持','课程满意度及反馈闭环']),
        ('教学交付与效果评估',['直播排期及助教协作','作业评阅与个别反馈','学习成果和完成标准核验','结课复盘及后续课程建议']),
        ('平台支持与资料管理',['账号开通和权限核验','课程资料版本维护','学习数据访问及备份','播放故障与工单处理'])]
    root={'id':'academy','label':'跨部门课程上线协作与教学质量管理','detail':'明确责任、交付物与反馈入口，支持持续改进。','children':[]}
    for i,(name,labels) in enumerate(teams):
        root['children'].append({'id':f'team-{i}','label':name,'children':[{'id':f'task-{i}-{j}','label':label,'detail':'形成可追溯的交付记录，并在异常出现时反馈给对应负责人。'} for j,label in enumerate(labels)]})
    tree={**base,'type':'tree','title':'从课程准备到学习成果：教育团队的完整责任分工','subtitle':'四个协作团队与十六项日常职责；层级只表示责任分解','root':root}
    labels=['顾客提交商品订单与配送信息','校验支付状态及收货地址','订单信息是否完整且有效','客服补全信息并再次确认','查询各仓库可用库存','库存是否满足本次订单','生成缺货处理工单并联系顾客','安排补货或协商替代方案','锁定库存并生成拣货任务','仓库拣货及批次核对','包装复核是否通过','重新拣货并登记差错原因','打印运单并移交承运商','同步配送进度与异常通知','顾客确认收货及服务评价','售后请求登记与责任分派','核验退换货条件与处理方案','归档订单、退款或换货记录']
    nodes=[{'id':f'n{i+1}','label':label,'detail':'核对必要信息并记录处理结果。','kind':'diamond' if i+1 in (3,6,11) else 'rect'} for i,label in enumerate(labels)]
    pairs=[(1,2,''),(2,3,''),(3,4,'信息需补充'),(4,2,'再次校验'),(3,5,'信息有效'),(5,6,''),(6,7,'库存不足'),(7,8,''),(8,5,'库存更新后复核'),(6,9,'库存充足'),(9,10,''),(10,11,''),(11,12,'复核不通过'),(12,10,'重新核对'),(11,13,'复核通过'),(13,14,''),(14,15,''),(15,16,'收到售后请求'),(16,17,''),(17,18,'处理完成')]
    retail={**base,'type':'graph','title':'订单履约与售后闭环','subtitle':'涵盖信息补全、库存不足和拣货差错三类异常；按箭头追踪实际去向','nodes':nodes,'edges':[{'from':f'n{a}','to':f'n{b}','label':label,'dashed':b<a} for a,b,label in pairs]}
    names=[('用户与业务入口',['顾客服务门户','商家商品管理工作台','运营活动配置后台','合作方开放接口','客户支持与工单入口','移动端订单查询入口','分析人员数据工作台','组织账号管理入口']),('应用与领域服务',['账号与权限服务','商品及价格服务','订单与售后服务','库存及仓储服务','支付状态核验服务','营销活动与优惠服务','通知与订阅服务','服务质量分析服务']),('数据与集成基础',['业务关系数据库','搜索与索引服务','文件和图片存储','事件消息队列','业务指标仓库','审计日志存储','外部合作方集成','归档与恢复管理'])]
    layers=[]
    for i,(name,items) in enumerate(names):
        layers.append({'label':name,'description':'此分层表示职责范围；只有明确给出的连线表示调用或数据关系。','items':[{'id':f's{i}-{j}','label':v,'detail':'提供独立职责边界与明确的访问入口。'} for j,v in enumerate(items)]})
    arch={**base,'type':'architecture','title':'多业务入口下的服务平台分层架构','subtitle':'每层八个模块，自动换行；支撑能力单独保留','layers':layers,'crosscut':['身份策略与访问审计','监控告警与运行追踪','版本配置与发布管理'],'edges':[{'from':'s0-0','to':'s1-2','label':'查询订单'},{'from':'s1-2','to':'s2-0','label':'读写订单记录'},{'from':'s1-6','to':'s2-3','label':'订阅通知事件'}]}
    product={**base,'type':'graph','title':'产品需求评审、交付验证与用户反馈的持续协作流程','subtitle':'长中文、英文标识及循环关系共同出现；内容与关系均保留','nodes':[{'id':'request','label':'收集用户反馈与业务问题','detail':'汇总访谈、客服工单和使用数据，区分已确认事实与待验证假设。'},{'id':'review','label':'需求评审与范围确认','detail':'明确验收标准、责任人及约束；TechnicalReview_2026_Sprint18 保留完整。'},{'id':'design','label':'交互设计与实现方案验证','detail':'检验关键流程和边界情形，准备让用户能够看懂并提出反馈的原型。'},{'id':'build','label':'开发、联调与数据迁移检查','detail':'各项变更关联至原始需求，记录测试证据及当前尚未验证的限制。'},{'id':'release','label':'发布后观察与效果复盘','detail':'结合用户反馈、业务指标和故障记录决定下一轮改进。'}],'edges':[{'from':'request','to':'review','label':'形成候选需求'},{'from':'review','to':'design','label':'范围已确认'},{'from':'design','to':'build','label':'方案达到交付条件'},{'from':'build','to':'release','label':'验收后发布'},{'from':'release','to':'request','label':'新的观察与反馈','dashed':True},{'from':'review','to':'review','label':'补充评审资料','dashed':True}]}
    return {'education-tree':tree,'retail-workflow':retail,'software-architecture':arch,'product-feedback':product}


def main():
    from render import render_file
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for key,data in examples().items():
        folder=out/key;folder.mkdir(exist_ok=True)
        source=folder/(key+'.json');source.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        result=render_file(source,folder)
        rows.append({'id':key,'title':data['title'],'result':result})
    (out/'report.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{'id':r['id'],'pages':r['result']['reading_view']['detail_pages'],'errors':r['result']['qa']['errors'],'warnings':r['result']['qa']['warnings']} for r in rows],ensure_ascii=False))


if __name__=='__main__':main()
