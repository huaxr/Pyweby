import bisect

def grade(score,breakpoints=[60, 70, 80, 90], grades='FDCBA'):
    i = bisect.bisect(breakpoints, score)
    return grades[i]

print([grade(score) for score in [33, 99, 77, 70, 89, 90, 100]])
#
# import bisect
# import random
#
# random.seed(1)
#
# print('New  Pos Contents')
# print('---  --- --------')
#
# l = []
# for i in range(1, 15):
#     r = random.randint(1, 100)
#     position = bisect.bisect(l, r)
#     bisect.insort(l, r)
#     print('%3d  %3d' % (r, position), l)