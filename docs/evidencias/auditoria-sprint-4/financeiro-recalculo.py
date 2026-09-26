from decimal import Decimal as D, ROUND_HALF_UP
r=lambda x,q='0.01': x.quantize(D(q),ROUND_HALF_UP)
H=2800
f=[("PLN",D('0.19'),17950),("back",D('0.19'),6050),("dados",D('0.13'),14250),("QA",D('0.13'),5900),("front",D('0.10'),6050),("GP",D('0.10'),10900),("arq",D('0.08'),15450),("UX",D('0.08'),4833)]
tot=D(0)
for n,p,s in f:
    h=p*H; vh=D(s)/160; c=h*vh
    print(n,h,r(vh),r(c),"| doc-rounded-rate cost",r(h*r(vh))); tot+=c
print("pessoal exato",r(tot))
ins=D(880*2+1440+500+625+1750); print("insumos",ins)
desp=D('4192.50')+7500+4000+1125+1750+750; print("desp",desp, "check 2795*.6*2.5",D(2795)*D('0.6')*D('2.5'), 12000*D('0.25')*D('2.5'))
pess=D('183699.95'); custos=pess+ins; base=custos+desp
print("custos",custos,"base",base,"desp/custos",r(desp/custos*100,'0.1'))
aliq=D('0.12076'); vl=r(base*D('1.15')); pf=r(vl/(1-aliq)); print("vl",vl,"pf",pf,"imp",r(pf*aliq),"lucro",vl-base, "lucro/pf", r((vl-base)/pf*100,'0.01'))
print("literal",r(base*(1+aliq)*D('1.15')), "dif", r((pf/r(base*(1+aliq)*D('1.15'))-1)*100,'0.01'))
print("rubric formula: imposto sobre base", r(base*aliq), "base c/ imp", r(base*(1+aliq)), "lucro 15%", r(base*(1+aliq)*D('0.15')))
print("hora", r(pf/H), "fatorR", r(pess/pf*100,'0.01'), "prolabore mes", r(pess/D('2.5')/7), r(pess/D('2.5')))
for p in ['0.30','0.245','0.21','0.14','0.105']: print("parc",p,r(pf*D(p)))
print("sum parc", sum(r(pf*D(p)) for p in ['0.30','0.245','0.21','0.14','0.105']))
# Anexo III effective faixa 4: 16% - 35640, need RBT12 X: (X*0.16-35640)/X = 0.12076 -> X=35640/(0.16-0.12076)
print("RBT12 implied", r(D(35640)/(D('0.16')-aliq)))
# cash flow
rec=[r(pf*D(p)) for p in ['0.30','0.245','0.21','0.14','0.105']]
pl=[0,r(pess/D('2.5')),r(pess/D('2.5')),r(pess/D('5')),0]
de=[0,r(desp/D('2.5')),r(desp/D('2.5')),r(desp/D('5')),0]
isn=[0,r(ins/D('2.5')),r(ins/D('2.5')),r(ins/D('5')),0]
acc=D(0)
for i in range(5):
    imp=r(rec[i]*aliq); s=rec[i]-pl[i]-de[i]-isn[i]-imp; acc+=s; print("mes",i,rec[i],pl[i],de[i],isn[i],imp,s,acc)
# contingencia
hrs=D('89.6')+64+D('38.4')+32+32+D('22.4'); vhm=pess/H; c=r(hrs*vhm); print("cont h",hrs, r(hrs/H*100,'0.1'), "vh",r(vhm), "custo",c, r(c/custos*100,'0.1'), "com imp", r(c/(1-aliq)), "teto", pf+r(c/(1-aliq)))
# sustentacao
for inf in [D('1185.99'),D('1236.92')]:
    b=inf+1205+400; m=r(b*D('0.15')); vl2=b+m; p=r(vl2/(1-D('0.0776'))); print("sust",b,m,vl2,p,p*12)
print("aws total", D('704')+288+71+100+D('8.47')+D('14.52'), "az", D('760.32')+D('311.04')+D('76.68')+65+D('18.33')+D('5.54'))
print("ia share aws", r((D('8.47')+D('14.52'))/D('1185.99')*100,'0.01'), r((D('18.33')+D('5.54'))/D('1236.92')*100,'0.01'))
print("anexoV price", r(vl/(1-D('0.1876'))), "diff", r((r(vl/(1-D('0.1876')))/pf-1)*100,'0.1'))
print("sust 24h valor-hora", r(D(1205)/24))
hrs2=D('89.6')*3+D('32')+D('22.4')+D('19.2'); c2=r(hrs2*vhm); print("cont revisada h",hrs2, r(hrs2/H*100,'0.1'), "custo",c2, r(c2/custos*100,'0.1'), "com imp", r(c2/(1-aliq)), "teto", pf+r(c2/(1-aliq)))
