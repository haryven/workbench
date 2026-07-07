## 使用脚本 

```shell
# 移植欧拉补丁
git rebase HEAD~20 --exec "git log -1 --pretty=format:%B > msg.txt && python3 rewrite_msg.py && git commit --amend -F msg.txt && rm msg.txt"
# 移植上游补丁
git rebase HEAD~7 --exec "git log -1 --pretty=format:%B > msg.txt && python3 upstream_msg.py msg.txt && git commit --amend -F msg.txt && rm msg.txt"
```

## 查询信息

```shell
# 查找某个commit来自哪个PR（有时候pr里没有列出commit）
  c=18d8205ef5af7a90fb6545aeb0017e82f3443fab
  since=$(git show -s --format=%ci $c)

  for m in $(git rev-list --first-parent --merges --reverse --since="$since" OLK-6.6); do
  	git merge-base --is-ancestor $c $m || continue
  	git merge-base --is-ancestor $c ${m}^1 && continue
  	git show -s --format='%H %s' $m
  	break
  done
```
