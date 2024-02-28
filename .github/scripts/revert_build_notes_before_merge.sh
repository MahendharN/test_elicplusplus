git config --local user.email "actions@github.com"
git config --local user.name "GitHub Actions"
BASE_BRANCH=$1
HEAD_BRANCH=$2
git checkout $BASE_BRANCH
cp build_notes.yaml build_notes1.yaml
cp taglist.yaml taglist1.yaml
git checkout $HEAD_BRANCH
mv build_notes1.yaml build_notes.yaml
mv taglist1.yaml taglist.yaml
git add build_notes.yaml taglist.yaml
git commit -m "ci(Unchange Build Notes): Build Notes and taglist changes reverted"
git push origin $HEAD_BRANCH

